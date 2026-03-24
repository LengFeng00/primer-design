
# 并行版引物设计工具使用说明（marker_design_parallel_v3.py）

该脚本用于基于 VCF 和参考基因组的多线程引物设计，具备如下功能：
- ✅ 使用 Primer3 本地设计引物；
- ✅ 多线程并行加速设计任务；
- ✅ 调用 BLAST 检查引物特异性；
- ✅ 自动模拟扩增产物并提取序列；
- ✅ 结果输出为制表符分割的 TSV 文件；
- ✅ 失败记录输出日志。

---

## 📦 环境依赖

建议使用 Conda 环境：

```bash
conda install -c bioconda blast
pip install primer3-py pyfaidx cyvcf2 pandas
```

---

## 🚀 命令行参数说明

```bash
python marker_design_parallel_v3.py \
  --vcf <输入VCF> \
  --fasta <参考基因组FASTA> \
  --len <提取长度，默认150> \
  --threads <并行线程数，默认4> \
  --out <输出TSV文件>
```

---

## 🧾 输出说明

| 字段名 | 说明 |
|--------|------|
| Chromosome | 染色体名称 |
| Position   | 变异位置（1-based） |
| Ref / Alt  | 碱基变异信息 |
| Variant_Type | SNP 或 InDel |
| Left/Right_Primer | 引物序列 |
| TM_Left / TM_Right | 退火温度 |
| GC_Left(%) / GC_Right(%) | 引物GC含量 |
| Product_Size | 扩增产物长度 |
| Product_GC(%) | 左右引物GC含量 |
| Amplicon_Sequence | 扩增序列 |
| Amplicon_GC(%) | 扩增产物GC含量 |
| Left/Right_Primer_Matches | 在基因组中匹配次数 |
| Left/Right_Primer_Unique | 是否唯一匹配 |

---

## 📤 日志文件
若出现无法设计、染色体缺失等错误，会记录到 `*.log` 文件中。

---

## ⚠️ 注意事项
- 若首次运行，会自动构建 BLAST 数据库；
- 支持任意数量的VCF变异；
- 如需产物长度筛选、引物位置限定可拓展。
