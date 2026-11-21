"""snap2flat.py SNAP.pkl OUT.bin [MB=128]: flat guest memory (low MB megabytes) of a harness.py snapshot, input of the JS recompiler runs. Run with -I."""
import pickle,sys
st,pages=pickle.load(open(sys.argv[1],'rb')); n=int(sys.argv[3]) if len(sys.argv)>3 else 128
m=bytearray(n<<20)
for p,d in pages.items():
    if p<len(m): m[p:p+4096]=d
open(sys.argv[2],'wb').write(m); print(len(pages),'pages')
