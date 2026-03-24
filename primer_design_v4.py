#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
并行引物设计工具 (优化版 v4)

功能：
- 基于 VCF 和参考基因组设计 PCR 引物
- 多线程并行加速
- BLAST 特异性检查（支持批处理优化）
- 扩增产物模拟
- 断点续传支持
- 进度条显示
- 详细的日志系统

Author: Optimized version
Date: 2026-03-24
"""

from __future__ import annotations

import argparse
import logging
import sys
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import json

import pandas as pd
import primer3
from cyvcf2 import VCF
from pyfaidx import Fasta
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import warnings

warnings.filterwarnings("ignore")

# ==================== 配置类 ====================

@dataclass
class PrimerConfig:
    """引物设计参数配置"""
    primer_opt_size: int = 20
    primer_min_size: int = 18
    primer_max_size: int = 25
    primer_opt_tm: float = 60.0
    primer_min_tm: float = 57.0
    primer_max_tm: float = 63.0
    primer_min_gc: float = 40.0
    primer_max_gc: float = 60.0
    product_size_ranges: List[Tuple[int, int]] = field(default_factory=lambda: [(100, 500)])
    max_pairs: int = 5

@dataclass
class BLASTConfig:
    """BLAST 检查配置"""
    task: str = "blastn-short"
    max_target_seqs: int = 10
    evalue: float = 1000
    word_size: int = 7
    batch_size: int = 100
    enable_batch: bool = True

@dataclass
class AppConfig:
    """应用配置"""
    threads: int = field(default_factory=lambda: min(4, cpu_count()))
    flank_length: int = 150
    enable_resume: bool = True
    checkpoint_file: str = ".primer_design_checkpoint.pkl"
    log_file: str = "primer_design.log"
    log_level: str = "INFO"
    chunk_size: int = 10
    max_retries: int = 3
    validate_input: bool = True

# ==================== 工具函数 ====================

def setup_logger(
    log_file: str,
    level: str = "INFO",
    console: bool = True
) -> logging.Logger:
    """
    配置日志系统

    Args:
        log_file: 日志文件路径
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        console: 是否输出到控制台

    Returns:
        配置好的 logger 对象
    """
    logger = logging.getLogger("primer_design")
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件 handler
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(getattr(logging, level.upper()))
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # 控制台 handler
    if console:
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger

def calculate_gc(seq: str) -> float:
    """
    计算序列 GC 含量

    Args:
        seq: DNA 序列

    Returns:
        GC 含量百分比
    """
    if not seq:
        return 0.0
    gc_count = sum(1 for base in seq.upper() if base in 'GC')
    return round((gc_count / len(seq)) * 100, 2)

def validate_input_files(
    vcf_file: Path,
    fasta_file: Path,
    logger: logging.Logger
) -> bool:
    """
    验证输入文件

    Args:
        vcf_file: VCF 文件路径
        fasta_file: FASTA 文件路径
        logger: 日志记录器

    Returns:
        验证是否通过
    """
    if not vcf_file.exists():
        logger.error(f"VCF 文件不存在: {vcf_file}")
        return False

    if not fasta_file.exists():
        logger.error(f"FASTA 文件不存在: {fasta_file}")
        return False

    if vcf_file.suffix not in ['.vcf', '.vcf.gz']:
        logger.error(f"VCF 文件格式错误，应为 .vcf 或 .vcf.gz: {vcf_file}")
        return False

    if fasta_file.suffix not in ['.fa', '.fasta', '.fna']:
        logger.error(f"FASTA 文件格式错误: {fasta_file}")
        return False

    return True

def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件

    Args:
        config_file: YAML 配置文件路径

    Returns:
        配置字典
    """
    default_config = {
        'primer': {
            'opt_size': 20,
            'min_size': 18,
            'max_size': 25,
            'opt_tm': 60.0,
            'min_tm': 57.0,
            'max_tm': 63.0,
            'min_gc': 40.0,
            'max_gc': 60.0,
            'product_size_ranges': [[100, 500]],
            'max_pairs': 5
        },
        'sequence': {
            'flank_length': 150
        },
        'blast': {
            'task': 'blastn-short',
            'max_target_seqs': 10,
            'evalue': 1000,
            'word_size': 7,
            'batch_size': 100,
            'enable_batch': True
        },
        'parallel': {
            'threads': min(4, cpu_count()),
            'chunk_size': 10
        },
        'logging': {
            'level': 'INFO',
            'file': 'primer_design.log',
            'console': True
        },
        'advanced': {
            'enable_resume': True,
            'checkpoint_interval': 50,
            'max_retries': 3,
            'validate_input': True
        }
    }

    if config_file and Path(config_file).exists():
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                # 合并配置
                for key in user_config:
                    if key in default_config and isinstance(default_config[key], dict):
                        default_config[key].update(user_config[key])
                    else:
                        default_config[key] = user_config[key]
        except ImportError:
            print("警告: 未安装 pyyaml，使用默认配置")
        except Exception as e:
            print(f"警告: 配置文件读取失败 ({str(e)})，使用默认配置")

    return default_config

# ==================== BLAST 优化模块 ====================

class BLASTChecker:
    """
    BLAST 特异性检查器

    支持单引物检查和批量检查，优化 I/O 性能
    """

    def __init__(
        self,
        db_prefix: Path,
        config: BLASTConfig,
        logger: logging.Logger
    ):
        """
        初始化 BLAST 检查器

        Args:
            db_prefix: BLAST 数据库前缀
            config: BLAST 配置
            logger: 日志记录器
        """
        self.db_prefix = db_prefix
        self.config = config
        self.logger = logger

    @staticmethod
    def build_blast_db(
        fasta_file: Path,
        db_prefix: Path,
        logger: logging.Logger
    ) -> bool:
        """
        构建 BLAST 数据库

        Args:
            fasta_file: FASTA 文件路径
            db_prefix: 数据库前缀
            logger: 日志记录器

        Returns:
            是否成功构建或已存在
        """
        if db_prefix.with_suffix(".nhr").exists():
            logger.info(f"BLAST 数据库已存在: {db_prefix}")
            return True

        import subprocess
        cmd = [
            "makeblastdb",
            "-in", str(fasta_file),
            "-dbtype", "nucl",
            "-out", str(db_prefix),
            "-parse_seqids"
        ]

        logger.info(f"正在构建 BLAST 数据库: {db_prefix}")
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("BLAST 数据库构建成功")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"BLAST 数据库构建失败: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("未找到 makeblastdb 命令，请安装 BLAST+")
            return False

    def check_primer(
        self,
        primer_seq: str
    ) -> List[Dict[str, Any]]:
        """
        单个引物 BLAST 检查

        Args:
            primer_seq: 引物序列

        Returns:
            BLAST 命中列表
        """
        import subprocess
        from tempfile import NamedTemporaryFile

        # 创建查询文件
        with NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".fa"
        ) as query_file:
            query_file.write(f">primer\n{primer_seq}\n")
            query_name = query_file.name

        output_file = Path(query_name).with_suffix(".blast.out")

        cmd = [
            "blastn",
            "-task", self.config.task,
            "-query", query_name,
            "-db", str(self.db_prefix),
            "-outfmt", "6 qseqid sseqid sstart send length mismatch evalue bitscore",
            "-max_target_seqs", str(self.config.max_target_seqs),
            "-evalue", str(self.config.evalue),
            "-word_size", str(self.config.word_size),
            "-out", str(output_file)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            hits = []
            if output_file.exists():
                with open(output_file) as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 8:
                            hits.append({
                                'qseqid': parts[0],
                                'sseqid': parts[1],
                                'sstart': int(parts[2]),
                                'send': int(parts[3]),
                                'length': int(parts[4]),
                                'mismatch': int(parts[5]),
                                'evalue': float(parts[6]),
                                'bitscore': float(parts[7])
                            })
            return hits

        except subprocess.CalledProcessError as e:
            self.logger.error(f"BLAST 查询失败: {e.stderr}")
            return []
        except FileNotFoundError:
            self.logger.error("未找到 blastn 命令，请安装 BLAST+")
            return []
        finally:
            # 清理临时文件
            Path(query_name).unlink(missing_ok=True)
            output_file.unlink(missing_ok=True)

    def check_primers_batch(
        self,
        primers: List[Tuple[str, str]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量 BLAST 检查（优化版）

        Args:
            primers: 引物列表 [(id, seq), ...]

        Returns:
            每个引物的命中结果 {id: [hits]}
        """
        if not primers:
            return {}

        # 如果批处理未启用或数量少，使用单引物模式
        if not self.config.enable_batch or len(primers) < 5:
            return {
                primer_id: self.check_primer(seq)
                for primer_id, seq in primers
            }

        import subprocess
        from tempfile import NamedTemporaryFile

        # 创建批量查询文件
        with NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".fa"
        ) as query_file:
            for primer_id, seq in primers:
                query_file.write(f">{primer_id}\n{seq}\n")
            query_name = query_file.name

        output_file = Path(query_name).with_suffix(".blast.out")

        cmd = [
            "blastn",
            "-task", self.config.task,
            "-query", query_name,
            "-db", str(self.db_prefix),
            "-outfmt", "6 qseqid sseqid sstart send length mismatch evalue bitscore",
            "-max_target_seqs", str(self.config.max_target_seqs),
            "-evalue", str(self.config.evalue),
            "-word_size", str(self.config.word_size),
            "-out", str(output_file)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            results = {primer_id: [] for primer_id, _ in primers}

            if output_file.exists():
                with open(output_file) as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 8:
                            primer_id = parts[0]
                            if primer_id in results:
                                results[primer_id].append({
                                    'sseqid': parts[1],
                                    'sstart': int(parts[2]),
                                    'send': int(parts[3]),
                                    'length': int(parts[4]),
                                    'evalue': float(parts[6])
                                })

            return results

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"批量 BLAST 查询失败: {str(e)}")
            # 降级到单引物模式
            return {
                primer_id: self.check_primer(seq)
                for primer_id, seq in primers
            }
        finally:
            # 清理临时文件
            Path(query_name).unlink(missing_ok=True)
            output_file.unlink(missing_ok=True)

# ==================== 引物设计模块 ====================

class PrimerDesigner:
    """引物设计器（封装 Primer3 调用）"""

    def __init__(
        self,
        config: PrimerConfig,
        logger: logging.Logger
    ):
        """
        初始化引物设计器

        Args:
            config: 引物设计配置
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger

    def design_primers(
        self,
        seq: str,
        target: Tuple[int, int],
        seq_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        使用 Primer3 设计引物

        Args:
            seq: 目标序列
            target: 目标区域 (start, length)
            seq_id: 序列标识符

        Returns:
            引物设计结果字典，失败返回 None
        """
        try:
            primer_result = primer3.bindings.designPrimers(
                {
                    'SEQUENCE_ID': seq_id,
                    'SEQUENCE_TEMPLATE': seq,
                    'SEQUENCE_TARGET': list(target)
                },
                {
                    'PRIMER_OPT_SIZE': self.config.primer_opt_size,
                    'PRIMER_MIN_SIZE': self.config.primer_min_size,
                    'PRIMER_MAX_SIZE': self.config.primer_max_size,
                    'PRIMER_OPT_TM': self.config.primer_opt_tm,
                    'PRIMER_MIN_TM': self.config.primer_min_tm,
                    'PRIMER_MAX_TM': self.config.primer_max_tm,
                    'PRIMER_MIN_GC': self.config.primer_min_gc,
                    'PRIMER_MAX_GC': self.config.primer_max_gc,
                    'PRIMER_PRODUCT_SIZE_RANGE': self.config.product_size_ranges,
                    'PRIMER_NUM_RETURN': self.config.max_pairs
                }
            )

            if primer_result['PRIMER_LEFT_NUM_RETURNED'] == 0:
                self.logger.debug(f"{seq_id}: 未设计到左侧引物")
                return None

            if primer_result['PRIMER_RIGHT_NUM_RETURNED'] == 0:
                self.logger.debug(f"{seq_id}: 未设计到右侧引物")
                return None

            return primer_result

        except Exception as e:
            self.logger.error(f"{seq_id}: Primer3 调用失败 - {str(e)}")
            return None

    def extract_primer_pair(
        self,
        primer_result: Dict[str, Any],
        pair_idx: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        从 Primer3 结果中提取单个引物对信息

        Args:
            primer_result: Primer3 返回的结果
            pair_idx: 引物对索引（默认 0）

        Returns:
            引物对信息字典，失败返回 None
        """
        left_key = f'PRIMER_LEFT_{pair_idx}_SEQUENCE'
        right_key = f'PRIMER_RIGHT_{pair_idx}_SEQUENCE'

        if left_key not in primer_result:
            return None

        return {
            'left_seq': primer_result[left_key],
            'right_seq': primer_result[right_key],
            'left_tm': primer_result[f'PRIMER_LEFT_{pair_idx}_TM'],
            'right_tm': primer_result[f'PRIMER_RIGHT_{pair_idx}_TM'],
            'left_start': primer_result[f'PRIMER_LEFT_{pair_idx}'][0],
            'right_start': primer_result[f'PRIMER_RIGHT_{pair_idx}'][0],
            'product_size': primer_result[f'PRIMER_PAIR_{pair_idx}_PRODUCT_SIZE']
        }

# ==================== 变异位点处理器 ====================

class VariantProcessor:
    """
    变异位点处理器

    封装完整的引物设计流程：序列提取 → Primer3 设计 → BLAST 检查 → 产物模拟
    """

    def __init__(
        self,
        genome: Fasta,
        designer: PrimerDesigner,
        blast_checker: BLASTChecker,
        flank_length: int,
        logger: logging.Logger,
        max_retries: int = 3
    ):
        """
        初始化处理器

        Args:
            genome: 参考基因组对象
            designer: 引物设计器
            blast_checker: BLAST 检查器
            flank_length: 侧翼序列长度
            logger: 日志记录器
            max_retries: 最大重试次数
        """
        self.genome = genome
        self.designer = designer
        self.blast_checker = blast_checker
        self.flank_length = flank_length
        self.logger = logger
        self.max_retries = max_retries

    def extract_sequence(
        self,
        chrom: str,
        start: int,
        end: int
    ) -> str:
        """
        安全提取基因组序列

        Args:
            chrom: 染色体名称
            start: 起始位置（0-based）
            end: 结束位置（0-based）

        Returns:
            基因组序列（大写）

        Raises:
            ValueError: 染色体不存在或提取失败
        """
        if chrom not in self.genome:
            raise ValueError(f"染色体 {chrom} 不存在于参考基因组中")

        seq = self.genome[chrom][start:end].seq.upper()

        if 'N' in seq:
            self.logger.warning(
                f"区域 {chrom}:{start}-{end} 包含未知碱基 N"
            )

        return seq

    def process_variant(
        self,
        record: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        处理单个变异位点

        流程：
        1. 提取侧翼序列
        2. Primer3 设计引物
        3. BLAST 特异性检查
        4. 提取扩增产物

        Args:
            record: 变异位点记录
            retry_count: 当前重试次数

        Returns:
            处理结果字典
        """
        chrom = record['CHROM']
        pos = record['POS'] - 1  # 转换为 0-based
        ref = record['REF']
        alt = record['ALT']

        variant_type = 'InDel' if len(ref) != len(alt) else 'SNP'
        seq_id = f"{chrom}_{record['POS']}"

        try:
            # 1. 提取序列
            start = max(pos - self.flank_length, 0)
            end = pos + len(ref) + self.flank_length
            seq = self.extract_sequence(chrom, start, end)
            target = [pos - start, max(len(ref), 1)]

            # 2. 设计引物
            primer_result = self.designer.design_primers(seq, target, seq_id)
            if not primer_result:
                return self._make_error_result(
                    record,
                    "无引物设计结果"
                )

            pair = self.designer.extract_primer_pair(primer_result, 0)
            if not pair:
                return self._make_error_result(
                    record,
                    "引物信息提取失败"
                )

            # 3. BLAST 检查
            left_hits = self.blast_checker.check_primer(pair['left_seq'])
            right_hits = self.blast_checker.check_primer(pair['right_seq'])

            # 4. 扩增产物模拟
            product_start = pair['left_start']
            product_end = pair['right_start'] + len(pair['right_seq'])
            amplicon_seq = seq[product_start:product_end]

            return {
                'Chromosome': chrom,
                'Position': record['POS'],
                'Ref': ref,
                'Alt': alt,
                'Variant_Type': variant_type,
                'Left_Primer': pair['left_seq'],
                'Right_Primer': pair['right_seq'],
                'TM_Left': round(pair['left_tm'], 2),
                'TM_Right': round(pair['right_tm'], 2),
                'GC_Left(%)': calculate_gc(pair['left_seq']),
                'GC_Right(%)': calculate_gc(pair['right_seq']),
                'Product_Size': pair['product_size'],
                'Product_GC(%)': calculate_gc(
                    pair['left_seq'] + pair['right_seq']
                ),
                'Amplicon_Sequence': amplicon_seq,
                'Amplicon_GC(%)': calculate_gc(amplicon_seq),
                'Left_Primer_Matches': len(left_hits),
                'Right_Primer_Matches': len(right_hits),
                'Left_Primer_Unique': "Yes" if len(left_hits) == 1 else "No",
                'Right_Primer_Unique': "Yes" if len(right_hits) == 1 else "No"
            }

        except Exception as e:
            self.logger.error(
                f"{seq_id} 处理失败: {str(e)}",
                exc_info=True
            )

            # 重试逻辑
            if retry_count < self.max_retries:
                self.logger.info(
                    f"{seq_id} 正在重试 ({retry_count + 1}/{self.max_retries})"
                )
                return self.process_variant(record, retry_count + 1)

            return self._make_error_result(
                record,
                f"异常: {str(e)}"
            )

    @staticmethod
    def _make_error_result(
        record: Dict[str, Any],
        message: str
    ) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'log': f"[{record['CHROM']}:{record['POS']}] {message}",
            'Chromosome': record['CHROM'],
            'Position': record['POS'],
            'Ref': record['REF'],
            'Alt': record['ALT'],
            'error': message
        }

# ==================== 多进程支持 ====================

_global_genome = None
_global_designer = None
_global_blast_checker = None
_global_processor = None
_global_config = None

def init_worker(
    fasta_path: str,
    primer_config: PrimerConfig,
    blast_config: BLASTConfig,
    db_prefix: str,
    app_config: AppConfig
):
    """
    初始化 worker 进程

    在每个子进程中独立加载参考基因组和配置对象
    """
    global _global_genome, _global_designer, _global_blast_checker
    global _global_processor, _global_config

    # 设置临时日志（避免多进程冲突）
    temp_logger = logging.getLogger("worker")
    temp_logger.setLevel(logging.WARNING)

    _global_config = app_config
    _global_genome = Fasta(fasta_path)
    _global_designer = PrimerDesigner(primer_config, temp_logger)
    _global_blast_checker = BLASTChecker(
        Path(db_prefix),
        blast_config,
        temp_logger
    )
    _global_processor = VariantProcessor(
        _global_genome,
        _global_designer,
        _global_blast_checker,
        app_config.flank_length,
        temp_logger,
        app_config.max_retries
    )

def process_record_wrapper(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    进程池包装函数

    使用全局变量避免序列化大对象
    """
    return _global_processor.process_variant(record)

# ==================== 主程序 ====================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="并行引物设计工具 (优化版 v4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s --vcf input.vcf --fasta ref.fa --out results.tsv
  %(prog)s --vcf input.vcf.gz --fasta ref.fa --threads 8 --len 200 --out results.tsv
  %(prog)s --vcf input.vcf --fasta ref.fa --config config.yaml --out results.tsv
        """
    )

    # 必需参数
    parser.add_argument(
        '--vcf',
        required=True,
        type=Path,
        help='输入 VCF 文件'
    )
    parser.add_argument(
        '--fasta',
        required=True,
        type=Path,
        help='参考基因组 FASTA 文件'
    )
    parser.add_argument(
        '--out',
        required=True,
        type=Path,
        help='输出 TSV 文件'
    )

    # 可选参数
    parser.add_argument(
        '--config',
        type=str,
        help='YAML 配置文件'
    )
    parser.add_argument(
        '--len',
        type=int,
        help='侧翼序列长度 (覆盖配置文件)'
    )
    parser.add_argument(
        '--threads',
        type=int,
        help='并行线程数 (覆盖配置文件)'
    )
    parser.add_argument(
        '--min-product',
        type=int,
        help='最小产物长度'
    )
    parser.add_argument(
        '--max-product',
        type=int,
        help='最大产物长度'
    )
    parser.add_argument(
        '--min-tm',
        type=float,
        help='最小退火温度'
    )
    parser.add_argument(
        '--max-tm',
        type=float,
        help='最大退火温度'
    )
    parser.add_argument(
        '--opt-tm',
        type=float,
        help='最优退火温度'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='禁用断点续传'
    )

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 命令行参数覆盖配置文件
    if args.len:
        config['sequence']['flank_length'] = args.len
    if args.threads:
        config['parallel']['threads'] = args.threads
    if args.no_resume:
        config['advanced']['enable_resume'] = False
    if args.min_product:
        config['primer']['product_size_ranges'][0][0] = args.min_product
    if args.max_product:
        config['primer']['product_size_ranges'][0][1] = args.max_product
    if args.min_tm:
        config['primer']['min_tm'] = args.min_tm
    if args.max_tm:
        config['primer']['max_tm'] = args.max_tm
    if args.opt_tm:
        config['primer']['opt_tm'] = args.opt_tm

    # 创建配置对象
    primer_config = PrimerConfig(
        primer_opt_size=config['primer']['opt_size'],
        primer_min_size=config['primer']['min_size'],
        primer_max_size=config['primer']['max_size'],
        primer_opt_tm=config['primer']['opt_tm'],
        primer_min_tm=config['primer']['min_tm'],
        primer_max_tm=config['primer']['max_tm'],
        primer_min_gc=config['primer']['min_gc'],
        primer_max_gc=config['primer']['max_gc'],
        product_size_ranges=[
            tuple(r) for r in config['primer']['product_size_ranges']
        ],
        max_pairs=config['primer']['max_pairs']
    )

    blast_config = BLASTConfig(
        task=config['blast']['task'],
        max_target_seqs=config['blast']['max_target_seqs'],
        evalue=config['blast']['evalue'],
        word_size=config['blast']['word_size'],
        batch_size=config['blast']['batch_size'],
        enable_batch=config['blast']['enable_batch']
    )

    app_config = AppConfig(
        threads=config['parallel']['threads'],
        flank_length=config['sequence']['flank_length'],
        enable_resume=config['advanced']['enable_resume'],
        log_file=config['logging']['file'],
        log_level=config['logging']['level'],
        chunk_size=config['parallel']['chunk_size'],
        max_retries=config['advanced']['max_retries']
    )

    # 初始化日志
    logger = setup_logger(
        app_config.log_file,
        app_config.log_level,
        config['logging']['console']
    )

    logger.info("=" * 60)
    logger.info("引物设计工具启动 (v4)")
    logger.info(f"VCF: {args.vcf}")
    logger.info(f"FASTA: {args.fasta}")
    logger.info(f"输出: {args.out}")
    logger.info(f"线程数: {app_config.threads}")
    logger.info(f"侧翼长度: {app_config.flank_length}")
    logger.info("=" * 60)

    # 1. 验证输入
    if config['advanced']['validate_input']:
        if not validate_input_files(args.vcf, args.fasta, logger):
            sys.exit(1)

    # 2. 读取 VCF
    logger.info("正在读取 VCF 文件...")
    try:
        vcf_reader = VCF(str(args.vcf))
        records = [
            {
                'CHROM': r.CHROM,
                'POS': r.POS,
                'REF': r.REF,
                'ALT': str(r.ALT[0]) if r.ALT else ''
            }
            for r in vcf_reader
        ]
        logger.info(f"共 {len(records)} 个变异位点")
    except Exception as e:
        logger.error(f"VCF 读取失败: {str(e)}")
        sys.exit(1)

    if not records:
        logger.warning("VCF 文件中没有变异位点")
        sys.exit(0)

    # 3. 构建 BLAST 数据库
    db_prefix = args.fasta.with_suffix(".blastdb")

    if not BLASTChecker.build_blast_db(args.fasta, db_prefix, logger):
        logger.error("BLAST 数据库构建失败")
        sys.exit(1)

    # 4. 检查断点续传
    checkpoint_file = Path(args.out).parent / ".primer_design_checkpoint.pkl"

    start_idx = 0
    if app_config.enable_resume and checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
                start_idx = checkpoint.get('processed_count', 0)
                logger.info(f"从检查点恢复: {start_idx}/{len(records)}")
        except Exception as e:
            logger.warning(f"检查点加载失败: {str(e)}")
            start_idx = 0

    # 5. 多进程并行处理
    logger.info(
        f"开始并行处理 (使用 {app_config.threads} 个进程)..."
    )

    results = []
    failures = []

    with Pool(
        processes=app_config.threads,
        initializer=init_worker,
        initargs=(
            str(args.fasta),
            primer_config,
            blast_config,
            str(db_prefix),
            app_config
        )
    ) as pool:
        # 创建进度条
        with tqdm(
            total=len(records) - start_idx,
            desc="处理进度",
            unit="位点"
        ) as pbar:

            # 分批处理
            batch_size = 100
            for i in range(start_idx, len(records), batch_size):
                batch = records[i:i + batch_size]

                # 使用 imap_unordered 提高性能
                for result in pool.imap_unordered(
                    process_record_wrapper,
                    batch
                ):
                    if 'log' in result:
                        failures.append(result['log'])
                    else:
                        results.append(result)

                    pbar.update(1)

                # 保存检查点
                if app_config.enable_resume:
                    try:
                        checkpoint = {
                            'processed_count': i + batch_size,
                            'timestamp': datetime.now().isoformat(),
                            'total': len(records)
                        }
                        with open(checkpoint_file, 'wb') as f:
                            pickle.dump(checkpoint, f)
                    except Exception as e:
                        logger.warning(f"检查点保存失败: {str(e)}")

    # 6. 保存结果
    if results:
        df = pd.DataFrame(results)

        # 排序
        sort_by = config.get('output', {}).get('sort_by', ['Chromosome', 'Position'])
        df = df.sort_values(sort_by)

        # 保存
        output_format = config.get('output', {}).get('format', 'tsv')

        if output_format == 'csv':
            df.to_csv(args.out, index=False)
        elif output_format == 'excel':
            df.to_excel(args.out.with_suffix('.xlsx'), index=False)
        else:  # tsv
            df.to_csv(args.out, sep='\t', index=False)

        logger.info(f"结果已保存至: {args.out}")
    else:
        logger.warning("没有成功设计的引物")
        # 创建空文件
        Path(args.out).touch()

    # 7. 保存失败记录
    if failures:
        fail_file = Path(args.out).with_suffix('.failures.tsv')
        fail_df = pd.DataFrame([{'log': f} for f in failures])
        fail_df.to_csv(fail_file, sep='\t', index=False)
        logger.info(f"失败记录已保存至: {fail_file}")

    # 8. 清理检查点
    if app_config.enable_resume and checkpoint_file.exists():
        try:
            checkpoint_file.unlink()
            logger.info("清理检查点文件")
        except Exception as e:
            logger.warning(f"检查点清理失败: {str(e)}")

    # 9. 汇总统计
    logger.info("=" * 60)
    logger.info("运行完成！")
    logger.info(f"总计: {len(records)} 个位点")
    logger.info(f"成功: {len(results)} 个")
    logger.info(f"失败: {len(failures)} 个")
    if len(records) > 0:
        logger.info(f"成功率: {len(results)/len(records)*100:.1f}%")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
