# 引物设计工具优化版 (v4) 使用指南

## 🚀 新增特性

### 相比 v3 的改进

| 特性 | v3 | v4 |
|------|----|----|
| **面向对象设计** | ❌ 全局变量 | ✅ 类封装 |
| **BLAST 批处理** | ❌ 每次创建临时文件 | ✅ 批量查询优化 |
| **进度显示** | ❌ 无 | ✅ tqdm 进度条 |
| **日志系统** | ❌ 简单日志 | ✅ 完整日志系统 |
| **断点续传** | ❌ 无 | ✅ 支持中断恢复 |
| **配置文件** | ❌ 参数硬编码 | ✅ YAML 配置 |
| **错误重试** | ❌ 无 | ✅ 自动重试机制 |
| **类型注解** | ❌ 无 | ✅ 完整类型提示 |
| **单元测试** | ❌ 无 | ✅ pytest 测试 |
| **依赖管理** | ❌ 无 | ✅ requirements.txt |
| **二聚体过滤** | ❌ 无 | ✅ 自动过滤高风险二聚体 |
| **背景SNP检查** | ❌ 无 | ✅ 规避已知SNP位点 |
| **BLAST结果缓存** | ❌ 无 | ✅ 跨进程共享缓存 |

---

## 📦 安装

### 1. 系统依赖

```bash
# 安装 BLAST+ (通过 conda)
conda install -c bioconda blast

# 或通过系统包管理器
# Ubuntu/Debian
sudo apt-get install ncbi-blast+

# CentOS/RHEL
sudo yum install blast+
```

### 2. Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 验证安装

```bash
# 检查 BLAST
makeblastdb -version
blastn -version

# 检查 Python 包
python -c "import primer3; import cyvcf2; import pyfaidx; print('OK')"
```

---

## 🎯 快速开始

### 基本用法

```bash
python primer_design_v4.py \
  --vcf input.vcf \
  --fasta reference.fa \
  --out results.tsv
```

### 使用配置文件

```bash
# 1. 复制并编辑配置文件
cp config.yaml my_config.yaml
vim my_config.yaml

# 2. 使用配置文件运行
python primer_design_v4.py \
  --vcf input.vcf \
  --fasta reference.fa \
  --config my_config.yaml \
  --out results.tsv
```

### 高级参数

```bash
python primer_design_v4.py \
  --vcf input.vcf \
  --fasta reference.fa \
  --out results.tsv \
  --threads 8 \
  --len 200 \
  --min-product 150 \
  --max-product 600 \
  --min-tm 58 \
  --max-tm 62 \
  --opt-tm 60
```

### 使用背景SNP检查（避免已知SNP）

```bash
python primer_design_v4.py \
  --vcf input.vcf \
  --fasta reference.fa \
  --out results.tsv \
  --bg-vcf known_snps.vcf.gz  # 提供已知SNP文件
```

### 禁用BLAST缓存（内存受限时）

```bash
python primer_design_v4.py \
  --vcf input.vcf \
  --fasta reference.fa \
  --out results.tsv \
  --no-blast-cache
```

---

## ⚙️ 配置文件详解

### config.yaml 结构

```yaml
# Primer3 参数
primer:
  opt_size: 20          # 最优引物长度
  min_size: 18          # 最小引物长度
  max_size: 25          # 最大引物长度
  opt_tm: 60.0          # 最优退火温度
  min_tm: 57.0          # 最小退火温度
  max_tm: 63.0          # 最大退火温度
  min_gc: 40.0          # 最小 GC 含量
  max_gc: 60.0          # 最大 GC 含量
  product_size_ranges:
    - [100, 500]        # 产物长度范围
  max_pairs: 5          # 每个位点返回的引物对数量
  # 二聚体/发夹结构过滤阈值
  max_self_any: 60.0    # 引物自身二聚体最大评分（越低越严格）
  max_self_end: 30.0    # 引物3'端自身二聚体最大评分
  max_pair_compl: 60.0  # 引物对之间二聚体最大评分
  max_pair_end: 30.0    # 引物对3'端之间二聚体最大评分
  max_hairpin_th: 30.0  # 发夹结构最大评分

# 序列提取参数
sequence:
  flank_length: 150     # 变异位点上下游提取长度

# BLAST 参数
blast:
  task: blastn-short    # BLAST 任务类型
  max_target_seqs: 10   # 最大目标序列数
  evalue: 1             # E-value 阈值（⚠️ 关键参数，影响引物特异性判断）
                        #   - 1: 严格（推荐用于短引物，可准确识别唯一匹配）
                        #   - 10-100: 中等（可能返回多个部分匹配）
                        #   - 1000+: 宽松（会返回大量低质量匹配，不建议）
  word_size: 7          # 字长
  batch_size: 100       # 批处理批次大小
  enable_batch: true    # 启用批处理优化

# 并行处理
parallel:
  threads: 4            # 并行进程数
  chunk_size: 10        # 任务块大小

# 输出设置
output:
  format: tsv           # 输出格式: tsv, csv, excel
  sort_by: [Chromosome, Position]
  include_failed: true

# 日志设置
logging:
  level: INFO           # DEBUG, INFO, WARNING, ERROR
  file: primer_design.log
  console: true

# 高级选项
advanced:
  enable_resume: true        # 启用断点续传
  checkpoint_interval: 50
  max_retries: 3            # 失败重试次数
  validate_input: true      # 输入验证
  background_vcf: null      # 背景SNP VCF文件（用于规避引物结合区的已知SNP）
  enable_blast_cache: true  # 启用BLAST结果缓存（提升性能）
```

---

## ✨ 新功能详解

### 1. 二聚体/发夹结构过滤

自动过滤可能形成二聚体或发夹结构的引物对，提高PCR成功率。

**配置参数：**
```yaml
primer:
  max_self_any: 60.0      # 引物自身二聚体评分（默认：60.0）
  max_self_end: 30.0      # 引物3'端自身二聚体评分（默认：30.0）
  max_pair_compl: 60.0    # 引物对间二聚体评分（默认：60.0）
  max_pair_end: 30.0      # 引物对3'端二聚体评分（默认：30.0）
  max_hairpin_th: 30.0    # 发夹结构评分（默认：30.0）
```

**评分说明：**
- 评分越低表示二聚体/发夹形成的可能性越小
- 建议根据具体实验需求调整阈值
- 过于严格的阈值可能导致无法设计出引物

### 2. 背景SNP检查

避免在已知SNP位点设计引物，提高引物特异性。

**使用场景：**
- 群体研究中避免多态性位点
- 设计物种特异性引物
- 提高PCR扩增稳定性

**使用方法：**
```bash
# 命令行
--bg-vcf population_snps.vcf.gz

# 或在配置文件中
advanced:
  background_vcf: population_snps.vcf.gz
```

**支持的VCF格式：**
- 压缩格式 (.vcf.gz)
- 未压缩格式 (.vcf)
- 需包含变异位点信息（CHROM, POS）

### 3. BLAST结果缓存

通过跨进程共享缓存，避免重复BLAST查询，显著提升性能。

**工作原理：**
```
进程1: 引物A → BLAST查询 → 缓存结果
进程2: 引物A → 从缓存读取（跳过BLAST）
```

**性能提升：**
- 对于大量位点，可节省30-50%的运行时间
- 内存占用增加约50-100MB（取决于引物数量）

**配置：**
```yaml
advanced:
  enable_blast_cache: true   # 启用（默认）
  # 或命令行
  # --no-blast-cache          # 禁用
```

---

## 📊 输出格式

### 成功结果 (TSV)

| Chromosome | Position | Ref | Alt | Variant_Type | Left_Primer | Right_Primer | TM_Left | TM_Right | Product_Size | ... |
|------------|----------|-----|-----|--------------|-------------|--------------|---------|----------|--------------|-----|
| chr1 | 12345 | A | G | SNP | ATCGATCG... | GCTAGCTA... | 58.5 | 59.2 | 250 | ... |

### 失败记录 (*.failures.tsv)

| log |
|-----|
| [chr1:12345] 染色体不存在于FASTA中 |
| [chr2:67890] 无引物设计结果 |

---

## 🔍 故障排除

### 问题 1: makeblastdb: command not found

**原因**: 未安装 BLAST+

**解决**:
```bash
conda install -c bioconda blast
```

### 问题 2: ModuleNotFoundError: No module named 'primer3'

**原因**: Python 依赖未安装

**解决**:
```bash
pip install -r requirements.txt
```

### 问题 3: 染色体不存在于FASTA中

**原因**: VCF 中的染色体名与 FASTA 不一致

**解决**: 检查并统一染色体命名（如 "chr1" vs "1"）

### 问题 4: BLAST 数据库构建失败

**原因**: FASTA 文件格式错误或路径问题

**解决**: 验证 FASTA 格式
```bash
# 检查 FASTA 格式
head -n 5 your.fasta

# 检查序列
faidx your.fasta
```

---

## 🧪 测试

### 运行单元测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_primer_design.py::TestUtilityFunctions -v

# 生成覆盖率报告
pytest tests/ --cov=. --cov-report=html
```

---

## 📈 性能优化建议

### 1. BLAST 批处理

```yaml
blast:
  enable_batch: true    # 启用批处理（推荐）
  batch_size: 100       # 根据内存调整
```

### 2. 并行线程数

```yaml
parallel:
  threads: 8            # 根据 CPU 核心数调整
```

### 3. 检查点间隔

```yaml
advanced:
  checkpoint_interval: 100  # 频繁保存（适合大批量任务）
```

---

## 🔄 从 v3 迁移

### 命令行对照

| v3 | v4 |
|----|----|
| `python marker_design_parallel_v3.py --vcf input.vcf --fasta ref.fa --len 150 --threads 4 --out out.tsv` | `python primer_design_v4.py --vcf input.vcf --fasta ref.fa --len 150 --threads 4 --out out.tsv` |

### 配置迁移

```bash
# v3: 参数硬编码
'PRIMER_OPT_SIZE': 20
'PRIMER_OPT_TM': 60.0

# v4: 配置文件
# config.yaml:
# primer:
#   opt_size: 20
#   opt_tm: 60.0
```

---

## 📝 最佳实践

### 1. 输入文件准备

```bash
# 压缩 VCF（推荐）
bgzip input.vcf
tabix -p vcf input.vcf.gz

# 索引 FASTA
samtools faidx reference.fa
```

### 2. 内存管理

```bash
# 对于大基因组，限制线程数
python primer_design_v4.py --threads 2 ...
```

### 3. 结果验证

```bash
# 查看失败记录
cat results.failures.tsv

# 检查引物特异性
awk '$12 > 1 || $13 > 1' results.tsv  # 非唯一匹配
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements.txt

# 代码格式化
black primer_design_v4.py

# 类型检查
mypy primer_design_v4.py

# 运行测试
pytest tests/ -v
```

---

## 📄 许可证

MIT License

---

## 📧 联系方式

- Issues: https://github.com/LengFeng00/primer-design/issues
- Email: [kanbl@webmail.hzau.edu.cn]
