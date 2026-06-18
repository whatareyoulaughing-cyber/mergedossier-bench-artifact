from mergedossier_bench.validators import validate_file


def test_toy_instance_validates():
    assert validate_file("examples/toy_pr_instance.json", "instance") == []


def test_toy_dossier_validates():
    assert validate_file("examples/toy_merge_dossier.json", "dossier") == []


def test_toy_annotation_validates():
    assert validate_file("examples/toy_annotation.json", "annotation") == []
