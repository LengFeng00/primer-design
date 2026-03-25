#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新功能：二聚体过滤、背景SNP检查、BLAST缓存
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_primer_config_with_dimer_params():
    """测试包含二聚体参数的配置类"""
    from primer_design_v4 import PrimerConfig

    config = PrimerConfig(
        max_self_any=50.0,
        max_self_end=25.0,
        max_pair_compl=55.0,
        max_pair_end=25.0,
        max_hairpin_th=25.0
    )

    assert config.max_self_any == 50.0
    assert config.max_self_end == 25.0
    assert config.max_pair_compl == 55.0
    assert config.max_pair_end == 25.0
    assert config.max_hairpin_th == 25.0

    print("✅ PrimerConfig 二聚体参数测试通过")


def test_app_config_with_bg_vcf():
    """测试包含背景VCF的配置类"""
    from primer_design_v4 import AppConfig

    config = AppConfig(
        background_vcf="/path/to/snps.vcf.gz",
        enable_blast_cache=True
    )

    assert config.background_vcf == "/path/to/snps.vcf.gz"
    assert config.enable_blast_cache is True

    print("✅ AppConfig 背景VCF和缓存参数测试通过")


def test_load_config_with_new_params():
    """测试加载包含新参数的配置文件"""
    from primer_design_v4 import load_config

    config = load_config("config.yaml")

    # 检查二聚体参数
    assert 'primer' in config
    assert 'max_self_any' in config['primer']
    assert config['primer']['max_self_any'] == 60.0

    # 检查高级参数
    assert 'advanced' in config
    assert 'background_vcf' in config['advanced']
    assert 'enable_blast_cache' in config['advanced']

    print("✅ 配置文件加载测试通过")


def test_blast_checker_with_cache():
    """测试BLAST检查器的缓存功能"""
    from primer_design_v4 import BLASTChecker, BLASTConfig
    import logging

    logging.basicConfig(level=logging.WARNING)

    # 创建模拟缓存
    from multiprocessing import Manager
    manager = Manager()
    cache = manager.dict()

    config = BLASTConfig(
        task="blastn-short",
        max_target_seqs=10,
        evalue=1000,
        word_size=7
    )

    # 创建临时数据库
    with tempfile.TemporaryDirectory() as tmpdir:
        db_prefix = Path(tmpdir) / "test_db"

        # 创建一个简单的FASTA文件
        fasta_file = Path(tmpdir) / "test.fa"
        with open(fasta_file, 'w') as f:
            f.write(">chr1\nATCGATCGATCGATCG\n")

        # 构建BLAST数据库
        import subprocess
        try:
            subprocess.run([
                "makeblastdb",
                "-in", str(fasta_file),
                "-dbtype", "nucl",
                "-out", str(db_prefix)
            ], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  BLAST未安装，跳过BLAST缓存测试")
            return

        checker = BLASTChecker(
            db_prefix,
            config,
            logging.getLogger(),
            shared_cache=cache
        )

        # 测试缓存功能
        assert checker.shared_cache is not None
        assert checker.shared_cache == cache

        print("✅ BLASTChecker 缓存功能测试通过")


def test_variant_processor_with_bg_vcf():
    """测试VariantProcessor的背景VCF功能"""
    from primer_design_v4 import (
        VariantProcessor,
        PrimerDesigner,
        BLASTChecker,
        BLASTConfig,
        PrimerConfig
    )
    from pyfaidx import Fasta
    import logging

    logging.basicConfig(level=logging.WARNING)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试FASTA文件
        fasta_file = Path(tmpdir) / "test.fa"
        with open(fasta_file, 'w') as f:
            f.write(">chr1\nATCGATCGATCGATCGATCGATCGATCGATCG\n")

        genome = Fasta(str(fasta_file))

        primer_config = PrimerConfig()
        blast_config = BLASTConfig()

        designer = PrimerDesigner(primer_config, logging.getLogger())
        blast_checker = BLASTChecker(
            Path(tmpdir) / "db",
            blast_config,
            logging.getLogger()
        )

        # 测试不带背景VCF的处理器（测试跳过逻辑）
        processor = VariantProcessor(
            genome,
            designer,
            blast_checker,
            flank_length=10,
            logger=logging.getLogger(),
            max_retries=1,
            background_vcf_reader=None  # 不提供背景VCF
        )

        assert processor.bg_vcf_reader is None

        # 测试SNP检查（应该返回False，因为没有背景VCF）
        has_snp, msg = processor.check_primers_for_snps(
            "chr1",
            (5, 10),
            (20, 10)
        )

        assert has_snp is False
        assert msg is None

        print("✅ VariantProcessor 背景SNP检查测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("运行新功能测试")
    print("=" * 60)

    try:
        test_primer_config_with_dimer_params()
        test_app_config_with_bg_vcf()
        test_load_config_with_new_params()
        test_blast_checker_with_cache()
        test_variant_processor_with_bg_vcf()

        print("\n" + "=" * 60)
        print("✅ 所有新功能测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
