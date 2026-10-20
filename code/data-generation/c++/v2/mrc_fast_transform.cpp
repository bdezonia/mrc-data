// Exact MRC row-transfer kernel modulo a 31-bit prime.
// Memory-optimized, occupancy-dependent bands (ragged coupling storage).
// The butterfly is identical mathematically to the v1 kernel:
//   (f0,f1) -> (f0+f1, f0 + y*f1).
// Output protocol is the exact same MRCMOD01 file as v1.
// Standard library only, C++17.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using u32 = std::uint32_t;
using u64 = std::uint64_t;

static inline u32 addmod(u32 a, u32 b, u32 p) {
    u32 v = a + b; // p < 2^31 ensures no overflow
    return v >= p ? v-p : v;
}
static std::size_t mulchecked(std::size_t a, std::size_t b) {
    if (b && a > std::numeric_limits<std::size_t>::max()/b)
        throw std::runtime_error("coefficient allocation overflow");
    return a*b;
}

struct Params {
    int r=0, c=0;
    u32 mod=0;
    std::string out, algorithm="butterfly";
    bool verbose=false;
    double memory_gb=16.0;
};
static Params parse(int argc, char** argv) {
    Params p;
    for(int i=1;i<argc;++i) {
        std::string k=argv[i];
        if(k=="--verbose") {p.verbose=true;continue;}
        if(i+1>=argc)throw std::runtime_error("missing value for "+k);
        std::string v=argv[++i];
        if(k=="--r")p.r=std::stoi(v);
        else if(k=="--c")p.c=std::stoi(v);
        else if(k=="--mod")p.mod=static_cast<u32>(std::stoul(v));
        else if(k=="--out")p.out=v;
        else if(k=="--memory-gb")p.memory_gb=std::stod(v);
        else if(k=="--algorithm")p.algorithm=v;
        else throw std::runtime_error("unknown option "+k);
    }
    if(p.r<1 || p.c<1 || p.out.empty() || p.mod<3 || p.mod>2147483647u)
        throw std::runtime_error("usage: --r R --c C --mod PRIME --out FILE [--memory-gb GIB] [--algorithm butterfly|naive] [--verbose]");
    if(p.algorithm!="butterfly" && p.algorithm!="naive")
        throw std::runtime_error("algorithm must be butterfly or naive");
    if(p.r>p.c)std::swap(p.r,p.c);
    if(p.r>=24)throw std::runtime_error("row mask width >= 24 is outside current kernel scope");
    if(p.memory_gb<=0)throw std::runtime_error("--memory-gb must be positive");
    return p;
}

// A rectangle of N=h*w cells and E=h*(w-1)+(h-1)*w edges has:
//   a <= min(E,2*o),   a >= max(0,E-4*(N-o)).
// During the in-place mask butterfly, multiplication by y increases the
// maximum degree by at most width. We reserve that padding PER OCCUPANCY,
// not across the entire dense (o,a) rectangle.
struct Block {
    int occmax, adjmax, padding;
    std::vector<int> lo, hi;
    std::vector<std::size_t> offsets;
    std::size_t stride;
    std::vector<u32> coeff;

    static std::size_t entries(int N, int E, int padding) {
        std::size_t total=0;
        for(int o=0;o<=N;++o) {
            int low=std::max(0,E-4*(N-o));
            int high=std::min(E,2*o)+padding;
            total+=static_cast<std::size_t>(high-low+1);
        }
        return total;
    }
    Block(std::size_t nmasks, int N, int E, int pad)
       :occmax(N),adjmax(E),padding(pad) {
        lo.resize(N+1);hi.resize(N+1);offsets.resize(N+1);
        stride=0;
        for(int o=0;o<=N;++o) {
            lo[o]=std::max(0,E-4*(N-o));
            hi[o]=std::min(E,2*o)+pad;
            offsets[o]=stride;
            stride+=static_cast<std::size_t>(hi[o]-lo[o]+1);
        }
        coeff.resize(mulchecked(nmasks,stride),0u);
    }
    u32* ptr(std::size_t mask,int o) {
        return coeff.data()+mask*stride+offsets[o];
    }
    const u32* ptr(std::size_t mask,int o) const {
        return coeff.data()+mask*stride+offsets[o];
    }
};

static std::vector<u32> compute(const Params& q) {
    const int w=q.r,h=q.c,nm=1<<w;
    std::vector<int> occ(nm),horiz(nm);
    for(int m=0;m<nm;++m) {
        occ[m]=__builtin_popcount(static_cast<unsigned>(m));
        horiz[m]=__builtin_popcount(static_cast<unsigned>(m & (m<<1)));
    }
    Block previous(nm,0,0,w);
    previous.coeff[0]=1;

    for(int row=0;row<h;++row) {
        auto tick=std::chrono::steady_clock::now();
        int N=(row+1)*w;
        int E=(row+1)*(w-1)+row*w;
        int pad=(row+1<h)?w:0;
        auto next_elements=mulchecked(static_cast<std::size_t>(nm),Block::entries(N,E,pad));
        long double mem=(static_cast<long double>(previous.coeff.size())+
                         static_cast<long double>(next_elements))*sizeof(u32);
        if(mem>q.memory_gb*1024.0L*1024.0L*1024.0L)
            throw std::runtime_error("estimated two-layer ragged RAM exceeds --memory-gb; no allocation attempted");
        Block next(nm,N,E,pad);
        if(q.algorithm=="butterfly") {
            for(int bit=0;bit<w;++bit) {
                int step=1<<bit;
                for(int b=0;b<nm;b+=2*step) {
                    for(int off=0;off<step;++off) {
                        int m0=b+off,m1=m0+step;
                        for(int o=0;o<=previous.occmax;++o) {
                            int lo=previous.lo[o];
                            int hi=std::min(previous.adjmax,2*o)+bit+1;
                            u32* a=previous.ptr(m0,o);
                            u32* c=previous.ptr(m1,o);
                            // Traverse from high to low, preserving unshifted c[j-1].
                            for(int j=hi;j>=lo;--j) {
                                int idx=j-lo;
                                u32 x=a[idx], y=c[idx];
                                c[idx]=addmod(x,idx>0?c[idx-1]:0u,q.mod);
                                a[idx]=addmod(x,y,q.mod);
                            }
                        }
                    }
                }
            }
            // For a destination mask T, vertical couplings are <= popcount(T).
            // This trims the temporary y^w padding down to actual support.
            for(int mask=0;mask<nm;++mask) {
                int os=occ[mask], as=horiz[mask];
                for(int o=0;o<=previous.occmax;++o) {
                    int no=o+os;
                    int low=std::max(previous.lo[o],next.lo[no]-as);
                    int high=std::min({previous.hi[o],std::min(previous.adjmax,2*o)+os,
                                       next.hi[no]-as});
                    if(low>high)continue;
                    const u32* from=previous.ptr(mask,o)+(low-previous.lo[o]);
                    u32* to=next.ptr(mask,no)+(low+as-next.lo[no]);
                    std::copy_n(from,static_cast<std::size_t>(high-low+1),to);
                }
            }
        } else {
            // Independently arranged conventional mask-pair transfer.
            for(int pm=0;pm<nm;++pm) {
                for(int mask=0;mask<nm;++mask) {
                    int os=occ[mask],as=horiz[mask]+__builtin_popcount(static_cast<unsigned>(pm&mask));
                    for(int o=0;o<=previous.occmax;++o) {
                        int no=o+os;
                        int low=std::max(previous.lo[o],next.lo[no]-as);
                        int high=std::min({previous.adjmax,previous.hi[o]-previous.padding,
                                           next.hi[no]-as});
                        if(low>high)continue;
                        const u32* from=previous.ptr(pm,o);
                        u32* to=next.ptr(mask,no);
                        for(int j=low;j<=high;++j) {
                            int idx=j+as-next.lo[no];
                            to[idx]=addmod(to[idx],from[j-previous.lo[o]],q.mod);
                        }
                    }
                }
            }
        }
        previous=std::move(next);
        if(q.verbose) {
            auto dt=std::chrono::duration<double>(std::chrono::steady_clock::now()-tick).count();
            std::cerr << "row="<<(row+1)<<"/"<<h<<" width="<<w
                      <<" o_max="<<previous.occmax<<" a_max="<<previous.adjmax
                      <<" ragged_layer_MiB="<<previous.coeff.size()*4.0/1048576.0
                      <<" sec="<<std::fixed<<std::setprecision(4)<<dt<<"\n";
        }
    }
    std::vector<u32> sums(mulchecked(static_cast<std::size_t>(previous.occmax+1),
                             static_cast<std::size_t>(previous.adjmax+1)),0u);
    for(int mask=0;mask<nm;++mask) {
        for(int o=0;o<=previous.occmax;++o) {
            const u32* from=previous.ptr(mask,o);
            u32* to=sums.data()+static_cast<std::size_t>(o)*(previous.adjmax+1);
            int low=previous.lo[o];
            for(int j=low;j<=previous.hi[o];++j) {
                to[j]=addmod(to[j],from[j-low],q.mod);
            }
        }
    }
    return sums;
}

static void write_mod(const Params& q, const std::vector<u32>& counts) {
    std::ofstream out(q.out,std::ios::binary);
    if(!out)throw std::runtime_error("cannot write "+q.out);
    const char magic[8]={'M','R','C','M','O','D','0','1'};
    out.write(magic,8);
    const u32 header[5]={static_cast<u32>(q.r),static_cast<u32>(q.c),q.mod,
        static_cast<u32>(q.r*q.c),static_cast<u32>(2*q.r*q.c-q.r-q.c)};
    out.write(reinterpret_cast<const char*>(header),sizeof(header));
    out.write(reinterpret_cast<const char*>(counts.data()),counts.size()*sizeof(u32));
    if(!out)throw std::runtime_error("write error "+q.out);
}
int main(int argc,char** argv) {
    try {
        auto q=parse(argc,argv);
        auto start=std::chrono::steady_clock::now();
        auto counts=compute(q);
        write_mod(q,counts);
        std::cerr<<"completed "<<q.r<<"x"<<q.c<<" mod="<<q.mod
                 <<" algorithm="<<q.algorithm<<" memory=ragged time_s="
                 <<std::fixed<<std::setprecision(3)
                 <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"\n";
    } catch(const std::exception& e) {
        std::cerr<<"ERROR: "<<e.what()<<"\n";
        return 1;
    }
    return 0;
}
