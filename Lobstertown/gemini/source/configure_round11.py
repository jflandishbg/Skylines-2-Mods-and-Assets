from pathlib import Path

r=Path(__file__).resolve().parent
for file in ("round11_geometry.py","house_parts.py"):
    p=r/file
    s=p.read_text(encoding="utf8").replace('"CanalStone"','"Dressed"')
    s="\n".join(line for line in s.split("\n") if "if False else None" not in line)
    p.write_text(s,encoding="utf8")
p=r/"bake_round5.py"
s=p.read_text(encoding="utf8").replace("Round 10","Round 11").replace("round10_geometry","round11_geometry")
s=s.replace('{"Z10":36}','{"Z1C":72,"Z1A":18}').replace('batch="R10"','batch="R11"')
a=s.index('    l,r,f,b=a["walls"]')
b=s.index('    for i in range',a)
s=s[:a]+s[b:]
a=s.index('            elif p.z>=2.9')
b=s.index('\n                roof+=1',a)
s=s[:a]+'            elif p.z>=2.64:'+s[b:]
s=s.replace('lo,hi=45,65','lo,hi=40,48').replace('<=.47,(n,physical)','<=.75,(n,physical)')
s=s.replace('            if not which or a["design"] in which:','            if a["colourway"]=="A" and (not which or a["design"] in which):')
p.write_text(s,encoding="utf8")
p=r/"scan_windows.py"
s=p.read_text(encoding="utf8").replace('def main():','def main(zone):').replace('ROOT/"import_Z10"','ROOT/f"import_{zone}"').replace('make("Z10")','make(zone)').replace('len(result)==36','len(result)=={"Z1C":72,"Z1A":18}[zone]').replace('    main()','    main(sys.argv[-1])')
p.write_text(s,encoding="utf8")
