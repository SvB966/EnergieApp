#!/usr/bin/env python
"""
Basale controle of alle packages uit environment.yml aanwezig zijn in de
doel-environment.  Exitcode 0 = OK, 1 = ontbrekende packages.
"""
import sys, subprocess, json, re, pathlib, textwrap
try:
    import yaml            # komt uit conda-forge
except ImportError:
    print("[FATAL] yaml-package ontbreekt; voer `conda install pyyaml` uit.", file=sys.stderr)
    sys.exit(1)

if len(sys.argv) != 3:
    sys.exit("Usage: verify_env_deps.py <environment.yml> <conda_env_name>")

yml_path, env_name = map(pathlib.Path, sys.argv[1:3])
deps = yaml.safe_load(yml_path.read_text())["dependencies"]

# 1) Maak platte lijst met <pkgname> zonder versie-pinnen
wanted = [re.split(r"[<=>]", d)[0].lower() for d in deps if isinstance(d, str)]

# 2) Haal ge-installeerde packages op
out = subprocess.check_output(
    ["conda", "list", "-n", env_name, "--json"], text=True, encoding="utf-8"
)
have = {pkg["name"].lower() for pkg in json.loads(out)}

missing = sorted(set(wanted) - have)
if missing:
    print(
        textwrap.dedent(
            f"""
            [ERROR] De volgende packages ontbreken in environment '{env_name}'
                    ondanks synchronisatie met environment.yml:
                    {', '.join(missing)}
            """
        ),
        file=sys.stderr,
    )
    sys.exit(1)

print("[INFO] Environment-scan succesvol: alle packages aanwezig.")
