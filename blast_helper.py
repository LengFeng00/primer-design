
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 用于运行 BLAST 以检查引物特异性

import subprocess
from pathlib import Path

def run_makeblastdb(fasta_file, db_prefix):
    cmd = [
        "makeblastdb",
        "-in", fasta_file,
        "-dbtype", "nucl",
        "-out", db_prefix
    ]
    subprocess.run(cmd, check=True)
    return f"{db_prefix}.nhr"  # 检查是否生成成功

def run_blastn(primer_seq, db_prefix, max_hits=10):
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(mode="w", delete=False) as query_file:
        query_file.write(f">primer\n{primer_seq}\n")
        query_name = query_file.name

    out_file = query_name + ".blast.out"
    cmd = [
        "blastn",
        "-task", "blastn-short",
        "-query", query_name,
        "-db", db_prefix,
        "-outfmt", "6 qseqid sseqid sstart send length mismatch evalue bitscore",
        "-max_target_seqs", str(max_hits),
        "-out", out_file
    ]
    subprocess.run(cmd, check=True)

    with open(out_file) as f:
        hits = [line.strip().split("\t") for line in f.readlines()]
    Path(query_name).unlink(missing_ok=True)
    Path(out_file).unlink(missing_ok=True)
    return hits
