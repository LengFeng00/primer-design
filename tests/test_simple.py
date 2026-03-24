#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版单元测试 - 不需要安装所有依赖

只测试基本的工具函数，可以快速验证核心逻辑
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_calculate_gc():
    """测试 GC 计算函数"""
    from primer_design_v4 import calculate_gc

    # 测试空序列
    assert calculate_gc("") == 0.0, "空序列应该是0%"
    print("✅ 空序列测试通过")

    # 测试全 AT
    assert calculate_gc("ATATAT") == 0.0, "全AT应该是0%"
    print("✅ 全AT测试通过")

    # 测试全 GC
    assert calculate_gc("GCGCGC") == 100.0, "全GC应该是100%"
    print("✅ 全GC测试通过")

    # 测试混合序列
    assert calculate_gc("ATGC") == 50.0, "ATGC应该是50%"
    print("✅ 混合序列测试通过")

    # 测试大小写不敏感
    assert calculate_gc("atgc") == calculate_gc("ATGC"), "应该大小写不敏感"
    print("✅ 大小写测试通过")

    print("\n🎉 所有GC计算测试通过！")


def test_config_classes():
    """测试配置类"""
    from primer_design_v4 import PrimerConfig, BLASTConfig, AppConfig

    # 测试 PrimerConfig
    primer_config = PrimerConfig()
    assert primer_config.primer_opt_size == 20, "默认引物大小应该是20"
    assert primer_config.primer_opt_tm == 60.0, "默认Tm应该是60"
    print("✅ PrimerConfig测试通过")

    # 测试 BLASTConfig
    blast_config = BLASTConfig()
    assert blast_config.task == "blastn-short", "默认任务应该是blastn-short"
    assert blast_config.enable_batch is True, "默认应该启用批处理"
    print("✅ BLASTConfig测试通过")

    # 测试 AppConfig
    app_config = AppConfig()
    assert app_config.enable_resume is True, "默认应该启用断点续传"
    assert app_config.max_retries == 3, "默认重试次数应该是3"
    print("✅ AppConfig测试通过")

    print("\n🎉 所有配置类测试通过！")


def test_load_config():
    """测试配置加载"""
    from primer_design_v4 import load_config

    # 测试默认配置
    config = load_config(None)
    assert 'primer' in config, "应该包含primer配置"
    assert 'blast' in config, "应该包含blast配置"
    assert 'parallel' in config, "应该包含parallel配置"

    # 验证默认值
    assert config['primer']['opt_size'] == 20, "默认引物大小应该是20"
    assert config['blast']['task'] == 'blastn-short', "默认BLAST任务"

    print("✅ 配置加载测试通过")
    print("\n🎉 配置加载测试通过！")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("运行简化版单元测试")
    print("=" * 60)
    print()

    try:
        # 运行测试
        test_calculate_gc()
        print()
        test_config_classes()
        print()
        test_load_config()

        print()
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("\n💡 提示：请先安装必要的依赖：")
        print("   pip install primer3-py pyfaidx cyvcf2 pandas tqdm pyyaml")
        sys.exit(1)

    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
