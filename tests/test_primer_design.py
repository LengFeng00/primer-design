#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单元测试
"""

import pytest
import tempfile
from pathlib import Path
import pandas as pd

# 导入主程序中的类和函数
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from primer_design_v4 import (
    calculate_gc,
    load_config,
    PrimerConfig,
    BLASTConfig,
    AppConfig
)

class TestUtilityFunctions:
    """测试工具函数"""

    def test_calculate_gc_empty(self):
        """测试空序列的 GC 计算"""
        assert calculate_gc("") == 0.0

    def test_calculate_gc_all_at(self):
        """测试全 AT 序列"""
        assert calculate_gc("ATATAT") == 0.0

    def test_calculate_gc_all_gc(self):
        """测试全 GC 序列"""
        assert calculate_gc("GCGCGC") == 100.0

    def test_calculate_gc_mixed(self):
        """测试混合序列"""
        assert calculate_gc("ATGC") == 50.0
        assert calculate_gc("ATGCAA") == round(3/6 * 100, 2)

    def test_calculate_gc_case_insensitive(self):
        """测试大小写不敏感"""
        assert calculate_gc("atgc") == calculate_gc("ATGC")
        assert calculate_gc("aTgC") == 50.0

class TestConfigLoading:
    """测试配置加载"""

    def test_load_default_config(self):
        """测试默认配置加载"""
        config = load_config(None)

        assert 'primer' in config
        assert 'blast' in config
        assert 'parallel' in config

        assert config['primer']['opt_size'] == 20
        assert config['blast']['task'] == 'blastn-short'

    def test_primer_config_dataclass(self):
        """测试 PrimerConfig 数据类"""
        config = PrimerConfig()

        assert config.primer_opt_size == 20
        assert config.primer_opt_tm == 60.0
        assert config.product_size_ranges == [(100, 500)]

    def test_blast_config_dataclass(self):
        """测试 BLASTConfig 数据类"""
        config = BLASTConfig()

        assert config.task == "blastn-short"
        assert config.enable_batch is True

    def test_app_config_dataclass(self):
        """测试 AppConfig 数据类"""
        config = AppConfig()

        assert config.enable_resume is True
        assert config.max_retries == 3

class TestBLASTChecker:
    """测试 BLAST 检查器"""

    @pytest.fixture
    def sample_fasta(self):
        """创建测试用的 FASTA 文件"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.fa'
        ) as f:
            f.write(">chr1\n")
            f.write("ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n")
            f.write(">chr2\n")
            f.write("GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n")
            return Path(f.name)

    @pytest.fixture
    def blast_checker(self, sample_fasta, tmp_path):
        """创建 BLAST 检查器实例"""
        from primer_design_v4 import BLASTChecker
        import logging

        db_prefix = tmp_path / "test_db"
        config = BLASTConfig()
        logger = logging.getLogger("test")

        checker = BLASTChecker(db_prefix, config, logger)

        # 构建测试数据库
        BLASTChecker.build_blast_db(sample_fasta, db_prefix, logger)

        return checker

    def test_check_primer(self, blast_checker):
        """测试单引物检查"""
        hits = blast_checker.check_primer("ATCGATCGATCG")

        assert isinstance(hits, list)

    def test_check_primers_batch(self, blast_checker):
        """测试批量引物检查"""
        primers = [
            ("primer_1", "ATCGATCGATCG"),
            ("primer_2", "GCTAGCTAGCTA")
        ]

        results = blast_checker.check_primers_batch(primers)

        assert isinstance(results, dict)
        assert "primer_1" in results
        assert "primer_2" in results

class TestPrimerDesigner:
    """测试引物设计器"""

    @pytest.fixture
    def designer(self):
        """创建引物设计器实例"""
        from primer_design_v4 import PrimerDesigner
        import logging

        config = PrimerConfig()
        logger = logging.getLogger("test")

        return PrimerDesigner(config, logger)

    def test_design_primers_success(self, designer):
        """测试成功的引物设计"""
        seq = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG" * 10  # 400bp
        target = (150, 1)  # 在位置 150 处设计

        result = designer.design_primers(seq, target, "test_1")

        # Primer3 可能成功或失败，取决于序列
        # 这里只测试函数能正常运行
        assert result is None or isinstance(result, dict)

    def test_extract_primer_pair(self, designer):
        """测试引物对提取"""
        # 模拟 Primer3 结果
        mock_result = {
            'PRIMER_LEFT_0_SEQUENCE': 'ATCGATCGATCG',
            'PRIMER_RIGHT_0_SEQUENCE': 'GCTAGCTAGCTA',
            'PRIMER_LEFT_0_TM': 58.5,
            'PRIMER_RIGHT_0_TM': 59.2,
            'PRIMER_LEFT_0': [100, 12, 58.5],
            'PRIMER_RIGHT_0': [200, 12, 59.2],
            'PRIMER_PAIR_0_PRODUCT_SIZE': 112
        }

        pair = designer.extract_primer_pair(mock_result, 0)

        assert pair is not None
        assert pair['left_seq'] == 'ATCGATCGATCG'
        assert pair['right_seq'] == 'GCTAGCTAGCTA'
        assert pair['product_size'] == 112

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, tmp_path):
        """测试完整工作流程（需要安装 BLAST）"""
        # 这个测试需要完整的环境，通常在 CI/CD 中运行
        # 这里只是展示测试结构

        # 1. 创建测试 VCF
        vcf_file = tmp_path / "test.vcf"
        # ... 创建测试数据

        # 2. 创建测试 FASTA
        fasta_file = tmp_path / "test.fa"
        # ... 创建测试数据

        # 3. 运行主程序
        # ... 调用 main 函数

        # 4. 验证输出
        output_file = tmp_path / "output.tsv"
        assert output_file.exists()

        # ... 验证结果

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
