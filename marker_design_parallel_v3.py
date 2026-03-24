
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 并行引物设计 + BLAST检查 + 扩增产物模拟，修复 Fasta 无法多进程传参问题

import argparse
import primer3
from pyfaidx import Fasta
from cyvcf2 import VCF
import pandas as pd
from pathlib import Path
from blast_helper import run_makeblastdb, run_blastn
from multiprocessing import Pool, cpu_count
import warnings

warnings.filterwarnings("ignore")

# 全局变量（供子进程使用）
genome = None

def init_worker(fasta_path):
    global genome
    genome = Fasta(fasta_path)

def calc_gc(seq):
    gc = sum(1 for base in seq if base in 'GCgc')
    return round((gc / len(seq)) * 100, 2) if seq else 0.0

def process_variant(args_tuple):
    record, db_prefix, flank_len = args_tuple
    try:
        chrom = record['CHROM']
        pos = record['POS'] - 1
        ref = record['REF']
        alt = record['ALT']
        variant_type = 'InDel' if len(ref) != len(alt) else 'SNP'

        if chrom not in genome:
            return {'log': f"[{chrom}:{pos}] 染色体不存在于FASTA中"}

        start = max(pos - flank_len, 0)
        end = pos + len(ref) + flank_len
        seq = genome[chrom][start:end].seq.upper()
        seq_target = [pos - start, max(len(ref), 1)]

        primer_result = primer3.bindings.designPrimers(
            {
                'SEQUENCE_ID': f"{chrom}_{pos}",
                'SEQUENCE_TEMPLATE': seq,
                'SEQUENCE_TARGET': seq_target
            },
            {
                'PRIMER_OPT_SIZE': 20,
                'PRIMER_MIN_SIZE': 18,
                'PRIMER_MAX_SIZE': 25,
                'PRIMER_OPT_TM': 60.0,
                'PRIMER_MIN_TM': 57.0,
                'PRIMER_MAX_TM': 63.0,
                'PRIMER_MIN_GC': 40.0,
                'PRIMER_MAX_GC': 60.0,
                'PRIMER_PRODUCT_SIZE_RANGE': [[100, 500]]
            }
        )

        if primer_result['PRIMER_LEFT_NUM_RETURNED'] == 0 or primer_result['PRIMER_RIGHT_NUM_RETURNED'] == 0:
            return {'log': f"[{chrom}:{pos+1}] 无引物设计结果"}

        left_primer = primer_result['PRIMER_LEFT_0_SEQUENCE']
        right_primer = primer_result['PRIMER_RIGHT_0_SEQUENCE']
        tm_left = primer_result['PRIMER_LEFT_0_TM']
        tm_right = primer_result['PRIMER_RIGHT_0_TM']
        product_size = primer_result['PRIMER_PAIR_0_PRODUCT_SIZE']
        gc_left = calc_gc(left_primer)
        gc_right = calc_gc(right_primer)
        gc_product = calc_gc(left_primer + right_primer)

        # BLAST 检查
        left_hits = run_blastn(left_primer, db_prefix)
        right_hits = run_blastn(right_primer, db_prefix)

        left_match_count = len(left_hits)
        right_match_count = len(right_hits)

        # 扩增产物模拟
        product_start = primer_result['PRIMER_LEFT_0'][0]
        product_end = primer_result['PRIMER_RIGHT_0'][0] + len(right_primer)
        amplicon_seq = seq[product_start:product_end]
        amplicon_gc = calc_gc(amplicon_seq)

        return {
            'Chromosome': chrom,
            'Position': pos + 1,
            'Ref': ref,
            'Alt': alt,
            'Variant_Type': variant_type,
            'Left_Primer': left_primer,
            'Right_Primer': right_primer,
            'TM_Left': round(tm_left, 2),
            'TM_Right': round(tm_right, 2),
            'GC_Left(%)': gc_left,
            'GC_Right(%)': gc_right,
            'Product_Size': product_size,
            'Product_GC(%)': gc_product,
            'Amplicon_Sequence': amplicon_seq,
            'Amplicon_GC(%)': amplicon_gc,
            'Left_Primer_Matches': left_match_count,
            'Right_Primer_Matches': right_match_count,
            'Left_Primer_Unique': "Yes" if left_match_count == 1 else "No",
            'Right_Primer_Unique': "Yes" if right_match_count == 1 else "No"
        }
    except Exception as e:
        return {'log': f"[{record['CHROM']}:{record['POS']}] 异常: {str(e)}"}

# 主程序入口
parser = argparse.ArgumentParser(description="多线程分子标记设计 + 引物唯一性检查 + 扩增产物模拟（修复Fasta并行）")
parser.add_argument('--vcf', required=True, help='VCF文件')
parser.add_argument('--fasta', required=True, help='参考基因组FASTA')
parser.add_argument('--len', type=int, default=150, help='变异上下游序列范围')
parser.add_argument('--threads', type=int, default=min(4, cpu_count()), help='并行线程数')
parser.add_argument('--out', required=True, help='输出TSV文件')
args = parser.parse_args()

# 读取VCF，转换为任务
vcf_reader = VCF(args.vcf)
records = [{
    'CHROM': r.CHROM,
    'POS': r.POS,
    'REF': r.REF,
    'ALT': str(r.ALT[0]) if r.ALT else ''
} for r in vcf_reader]

# 构建BLAST库
db_prefix = args.fasta + ".blastdb"
if not Path(db_prefix + ".nhr").exists():
    print("正在构建BLAST数据库...")
    run_makeblastdb(args.fasta, db_prefix)

# 构造任务参数
tasks = [(r, db_prefix, args.len) for r in records]

# 启动进程池，传入Fasta路径以便各子进程初始化
with Pool(processes=args.threads, initializer=init_worker, initargs=(args.fasta,)) as pool:
    results_all = pool.map(process_variant, tasks)

# 拆分成功与失败
success = [r for r in results_all if isinstance(r, dict) and 'Left_Primer' in r]
failures = [r['log'] for r in results_all if isinstance(r, dict) and 'log' in r]

# 写出结果
df = pd.DataFrame(success)
df.to_csv(args.out, sep='\t', index=False)

# 日志
if failures:
    log_file = Path(args.out).with_suffix('.log')
    with open(log_file, 'w', encoding='utf-8') as f:
        for line in failures:
            f.write(line + '\n')

print(f"运行完成：成功 {len(success)} 条，失败 {len(failures)} 条。")
