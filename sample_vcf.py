
import random
import argparse
from pathlib import Path

def sample_vcf(input_vcf, output_vcf, n):
    with open(input_vcf, 'r') as f:
        header = []
        records = []
        for line in f:
            if line.startswith('#'):
                header.append(line)
            else:
                records.append(line)

    if n > len(records):
        print(f"警告：请求抽取 {n} 条记录，但VCF中仅有 {len(records)} 条变异。将全部输出。")
        n = len(records)

    sampled = random.sample(records, n)

    with open(output_vcf, 'w') as out:
        out.writelines(header)
        out.writelines(sampled)

    print(f"已抽取 {n} 条变异信息，保存至 {output_vcf}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="从VCF文件中随机抽取n个变异记录")
    parser.add_argument('--vcf', required=True, help="输入VCF文件路径")
    parser.add_argument('--out', required=True, help="输出VCF文件路径")
    parser.add_argument('-n', type=int, required=True, help="抽取的变异数量")
    args = parser.parse_args()

    sample_vcf(args.vcf, args.out, args.n)
