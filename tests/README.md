# 测试指南

## 📋 测试文件说明

| 文件 | 说明 | 依赖要求 |
|------|------|---------|
| `test_primer_design.py` | 完整单元测试 | 需要安装所有依赖 |
| `test_simple.py` | 简化测试（推荐） | 只需核心依赖 |

---

## 🚀 快速开始

### 方法 1：运行简化测试（推荐）

```bash
# 1. 安装核心依赖
pip install primer3-py pyfaidx pandas tqdm pyyaml

# 2. 运行简化测试
cd tests
python test_simple.py
```

**输出示例**：
```
============================================================
运行简化版单元测试
============================================================

✅ 空序列测试通过
✅ 全AT测试通过
✅ 全GC测试通过
✅ 混合序列测试通过
✅ 大小写测试通过

🎉 所有GC计算测试通过！

✅ PrimerConfig测试通过
✅ BLASTConfig测试通过
✅ AppConfig测试通过

🎉 所有配置类测试通过！

✅ 配置加载测试通过

🎉 配置加载测试通过！

============================================================
✅ 所有测试通过！
============================================================
```

### 方法 2：运行完整测试（需要 pytest）

```bash
# 1. 安装所有依赖
pip install -r ../requirements.txt

# 2. 运行完整测试
cd tests
pytest test_primer_design.py -v

# 或运行覆盖率测试
pytest test_primer_design.py --cov=.. --cov-report=html
```

---

## 📦 依赖安装

### 最小依赖（运行简化测试）

```bash
pip install primer3-py pyfaidx pandas tqdm pyyaml
```

### 完整依赖（运行完整测试）

```bash
# Python 依赖
pip install -r requirements.txt

# BLAST+ (系统依赖，用于 BLAST 测试)
conda install -c bioconda blast
```

---

## 🔧 测试说明

### 简化测试（test_simple.py）

**测试内容**：
- ✅ GC 含量计算函数
- ✅ 配置类初始化
- ✅ 配置文件加载

**运行时间**：< 1秒
**依赖要求**：核心 Python 包

### 完整测试（test_primer_design.py）

**测试内容**：
- ✅ 工具函数（5个测试）
- ✅ 配置加载（4个测试）
- ✅ BLAST 检查器（2个测试）
- ✅ 引物设计器（2个测试）
- ✅ 集成测试（1个测试，未完成）

**运行时间**：5-10秒（需要 BLAST）
**依赖要求**：完整 Python 环境 + BLAST+

---

## 🐛 常见问题

### Q1: ModuleNotFoundError: No module named 'pytest'

**原因**：未安装 pytest

**解决**：
```bash
pip install pytest pytest-cov
```

### Q2: ImportError: No module named 'primer3'

**原因**：未安装核心依赖

**解决**：
```bash
pip install primer3-py pyfaidx cyvcf2 pandas tqdm
```

### Q3: BLAST 测试失败

**原因**：未安装 BLAST+

**解决**：
```bash
conda install -c bioconda blast
```

或者跳过 BLAST 测试：
```bash
pytest test_primer_design.py -v -k "not BLAST"
```

### Q4: ImportError: cannot import name 'calculate_gc'

**原因**：路径问题，无法导入 primer_design_v4

**解决**：
```bash
# 确保在项目根目录运行
cd /path/to/primer-design-master
python tests/test_simple.py
```

---

## 📊 测试覆盖率

运行覆盖率测试：

```bash
# 安装覆盖率工具
pip install pytest-cov

# 运行覆盖率测试
pytest tests/ --cov=. --cov-report=html

# 查看报告
firefox htmlcov/index.html
```

---

## 🧪 测试开发

### 添加新测试

1. 在 `tests/` 目录下创建测试文件
2. 使用标准 pytest 命名：`test_*.py`
3. 定义测试类：`class TestSomething`
4. 定义测试方法：`def test_something(self)`

示例：
```python
class TestNewFeature:
    """测试新功能"""

    def test_basic(self):
        """基础测试"""
        assert True

    def test_advanced(self):
        """高级测试"""
        assert 1 + 1 == 2
```

### 运行特定测试

```bash
# 运行特定测试文件
pytest tests/test_simple.py

# 运行特定测试类
pytest tests/test_simple.py::TestUtilityFunctions

# 运行特定测试方法
pytest tests/test_simple.py::TestUtilityFunctions::test_calculate_gc

# 运行匹配名称的测试
pytest tests/ -k "gc"
```

---

## 📝 测试最佳实践

### 1. 测试命名

- ✅ 好的命名：`test_calculate_gc_empty`
- ❌ 不好的命名：`test1`

### 2. 测试结构

```python
def test_something():
    # Arrange（准备）
    input_data = "ATGC"

    # Act（执行）
    result = calculate_gc(input_data)

    # Assert（断言）
    assert result == 50.0
```

### 3. 测试独立性

每个测试应该独立运行，不依赖其他测试：

```python
# ✅ 好的测试
def test_feature_1():
    data = create_test_data()
    assert process(data) == expected

def test_feature_2():
    data = create_test_data()  # 重新创建
    assert process(data) == expected

# ❌ 不好的测试
def test_feature_1():
    global.data = create_test_data()

def test_feature_2():
    assert process(global.data) == expected  # 依赖 test_feature_1
```

---

## 🔍 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ -v
```

---

## 📚 相关资源

- [pytest 官方文档](https://docs.pytest.org/)
- [Python 测试最佳实践](https://docs.python-guide.org/writing/tests/)
- [项目测试覆盖率报告](https://coveralls.io/)

---

*最后更新: 2026-03-24*
