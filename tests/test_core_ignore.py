from src.core.ignore import should_ignore_dir, should_ignore_file


def test_ignore_rules_skip_dependency_cache_dirs():
    """验证共享忽略规则会跳过依赖、缓存和版本控制目录。"""
    assert should_ignore_dir(".git")
    assert should_ignore_dir("node_modules")
    assert should_ignore_dir("__pycache__")
    assert not should_ignore_dir("src")


def test_ignore_rules_skip_noise_files_and_suffixes():
    """验证共享忽略规则会跳过系统噪声文件和生成文件后缀。"""
    assert should_ignore_file(".DS_Store")
    assert should_ignore_file("module.pyc")
    assert should_ignore_file("server.log")
    assert not should_ignore_file("app.py")
