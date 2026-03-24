# VCF 文件要求说明

## 📋 必需字段

该工具需要 VCF 文件包含以下标准字段：

| 字段 | 说明 | 示例 | 要求 |
|------|------|------|------|
| **CHROM** | 染色体名称 | `chr1`, `1` | 必须与 FASTA 一致 |
| **POS** | 变异位置（1-based） | `12345` | 正整数 |
| **REF** | 参考碱基 | `A`, `AT` | A/T/C/G/N 或其组合 |
| **ALT** | 变异碱基 | `G`, `GT` | 至少一个 ALT |

---

## ✅ 支持的特性

### 1. 文件格式

- ✅ 未压缩 VCF (`.vcf`)
- ✅ 压缩 VCF (`.vcf.gz`)
- ✅ 标准 VCF v4.0/v4.1/v4.2

### 2. 变异类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **SNP** | 单核苷酸多态性 | `A → G` |
| **InDel** | 插入缺失 | `AT → A` (缺失) 或 `A → AT` (插入) |
| **MNP** | 多核苷酸多态性 | `AT → CG` |

### 3. ALT 等位基因

- ✅ 单个 ALT：`ALT=G`
- ✅ 多个 ALT：`ALT=G,T,A`（只使用第一个 `G`）

### 4. 染色体类型

- ✅ 常染色体：`chr1-chr22` 或 `1-22`
- ✅ 性染色体：`chrX`, `chrY` 或 `X`, `Y`
- ✅ 线粒体：`chrM` 或 `MT`
- ✅ 其他 contig/scaffold

---

## ❌ 不支持的情况

### 1. 结构变异 (SV)

- ❌ CNV（拷贝数变异）
- ❌ 倒位
- ❌ 易位
- ❌ 大片段插入/缺失（>50bp）

**原因**：Primer3 设计的是短片段 PCR 引物（通常 100-500bp）

### 2. 复杂变异

- ❌ 大于 50bp 的 InDel
- ❌ 多个 ALT 的组合分析

### 3. 特殊记录

- ❌ FILTER 列不为 "PASS" 的位点
- ❌ 没有 ALT 的记录

---

## ⚠️ 重要注意事项

### 1. 染色体名称一致性

**VCF 和 FASTA 中的染色体名必须完全一致**

✅ **正确示例**：
```
VCF:    chr1, chr2, chrX
FASTA:  >chr1, >chr2, >chrX
```

❌ **错误示例**：
```
VCF:    chr1, chr2, chrX
FASTA:  >1, >2, >X
```

**检查方法**：
```bash
# 查看 VCF 中的染色体
bcftools query -l input.vcf.gz

# 查看 FASTA 中的染色体
samtools faidx reference.fa
```

### 2. 坐标系统

- VCF 使用 **1-based** 坐标（标准 VCF 格式）
- 工具内部转换为 **0-based** 处理
- 输出恢复为 **1-based**

**示例**：
```
VCF:   POS=100  (1-based, 第100个碱基)
代码:  pos=99   (0-based, 索引99)
输出:  Position=100  (1-based)
```

### 3. 多 ALT 处理

**只使用第一个 ALT 等位基因**

```
VCF:  ALT=G,T,A
使用: G (第一个)
```

### 4. 坐标范围

**变异位置 + 侧翼长度 不能超出染色体长度**

```
示例：
染色体长度: 10,000 bp
变异位置: POS=9,900
侧翼长度: 150
结束位置: 9,900 + 150 = 10,050 ❌ 超出范围
```

**解决方案**：
```bash
# 过滤掉靠近染色体末端的位点
bcftools view -i 'POS < 9950' input.vcf.gz > filtered.vcf
```

---

## 📝 VCF 文件示例

### 标准 VCF 格式

```vcf
##fileformat=VCFv4.2
##fileDate=20250324
##source=primer-design
##reference=reference.fa
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
#CHROM POS ID REF ALT QUAL FILTER INFO FORMAT SAMPLE
chr1   12345   .  A   G   100  PASS  DP=50   GT  0/1
chr1   67890   .  AT  A   80   PASS  DP=30   GT  1/1
chr2   54321   .  C   CT  90   PASS  DP=40   GT  0/1
chrX   98765   .  T   TA,C 70  PASS  DP=25   GT  0/1
```

### 最小 VCF 格式

```vcf
##fileformat=VCFv4.2
#CHROM POS ID REF ALT QUAL FILTER INFO
chr1   1000   .  A   G   .   .    .
chr2   2000   .  C   T   .   .    .
```

---

## 🔧 VCF 文件准备

### 1. 压缩 VCF（推荐）

```bash
# 压缩
bgzip input.vcf

# 创建索引
tabix -p vcf input.vcf.gz
```

**优势**：
- 文件更小
- 访问更快
- 支持区域查询

### 2. 验证 VCF 格式

```bash
# 使用 vcftools 验证
vcf-validator input.vcf

# 使用 bcftools 检查
bcftools stats input.vcf.gz
```

### 3. 过滤位点（可选）

```bash
# 只保留 PASS 位点
bcftools view -i 'FILTER="PASS"' input.vcf.gz > filtered.vcf.gz

# 过滤 SNP
bcftools view -v snps input.vcf.gz > snps.vcf.gz

# 过滤 InDel
bcftools view -v indels input.vcf.gz > indels.vcf.gz

# 按深度过滤
bcftools view -i 'DP>10' input.vcf.gz > high_depth.vcf.gz
```

### 4. 提取特定区域（可选）

```bash
# 提取特定染色体
bcftools view -r chr1 input.vcf.gz > chr1.vcf.gz

# 提取特定区域
bcftools view -r chr1:1-1000000 input.vcf.gz > region.vcf.gz
```

### 5. 修改染色体名称（如需要）

```bash
# 添加 chr 前缀
bcftools annotate --rename-chrs <(echo -e "1\tchr1\n2\tchr2") input.vcf.gz -Oz -o with_chr.vcf.gz

# 去除 chr 前缀
bcftools annotate --rename-chrs <(echo -e "chr1\t1\nchr2\t2") input.vcf.gz -Oz -o without_chr.vcf.gz
```

---

## 📊 数据量建议

| 位点数量 | 推荐配置 | 预计耗时 | 内存占用 |
|---------|---------|---------|---------|
| < 100 | 线程数=2 | < 1分钟 | ~200 MB |
| 100-1,000 | 线程数=4 | 1-5分钟 | ~400 MB |
| 1,000-10,000 | 线程数=8 | 5-30分钟 | ~800 MB |
| > 10,000 | 线程数=16 | > 30分钟 | ~1.5 GB |

**建议**：
- 位点数 > 1,000 时，使用压缩 VCF (`.vcf.gz`)
- 位点数 > 10,000 时，考虑分批处理

---

## 🧪 创建测试 VCF

### 方法 1：使用 echo

```bash
cat > test.vcf << 'EOF'
##fileformat=VCFv4.2
##reference=test.fa
#CHROM POS ID REF ALT QUAL FILTER INFO
chr1   1000   .  A   G   100  PASS  .
chr1   2000   .  AT  A   100  PASS  .
chr2   3000   .  C   T   100  PASS  .
EOF

cat > test.fa << 'EOF'
>chr1
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
>chr2
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA
EOF
```

### 方法 2：使用 Python

```python
# create_test_vcf.py
vcf_content = """##fileformat=VCFv4.2
##reference=test.fa
#CHROM POS ID REF ALT QUAL FILTER INFO
chr1   1000   .  A   G   100  PASS  .
chr1   2000   .  AT  A   100  PASS  .
chr2   3000   .  C   T   100  PASS  .
"""

with open('test.vcf', 'w') as f:
    f.write(vcf_content)

fasta_content = """>chr1
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
>chr2
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA
"""

with open('test.fa', 'w') as f:
    f.write(fasta_content)
```

---

## 🔍 常见问题

### Q1: 为什么出现"染色体不存在于FASTA中"错误？

**原因**：VCF 和 FASTA 的染色体名称不一致

**解决**：
```bash
# 检查不一致的染色体
comm -23 <(bcftools query -l input.vcf.gz | sort) \
          <(cut -f1 reference.fa.fai | sort)

# 统一命名（添加 chr 前缀）
bcftools annotate --rename-chrs chr_map.txt input.vcf.gz -Oz -o fixed.vcf.gz
```

### Q2: 能否使用 GVCF 文件？

**答**：可以，但需要先提取变异位点

```bash
bcftools view -g 'gt="0/1" || gt="1/1"' input.g.vcf.gz > variants.vcf.gz
```

### Q3: 如何处理多样本 VCF？

**答**：工具会处理所有样本，但为每个变异位点只设计一对引物

### Q4: 是否需要先做 VCF 质控？

**答**：建议做基本质控

```bash
# 基本质控
bcftools stats input.vcf.gz > stats.txt
bcftools view -i 'FILTER="PASS" && QUAL>30' input.vcf.gz > filtered.vcf.gz
```

---

## 📖 参考资料

- [VCF 格式规范](https://samtools.github.io/hts-specs/VCFv4.2.pdf)
- [bcftools 文档](http://samtools.github.io/bcftools/bcftools.html)
- [cyvcf2 文档](https://brentp.github.io/cyvcf2/)

---

*最后更新: 2026-03-24*
