// Exact MRC row-transfer kernel modulo a small prime.
// Butterfly over row masks: (f0,f1) -> (f0+f1, f0 + y*f1).
// A Python driver performs CRT over enough primes to recover exact counts.
// Standard library only. C++17.
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

static u32 addmod(u32 a, u32 b, u32 p) {
    // p <= 2^31-1, so the two residues add without uint32 overflow.
    u32 v = a + b;
    return v >= p ? v - p : v;
}

static std::size_t checked_product(std::size_t x, std::size_t y) {
    if (y && x > std::numeric_limits<std::size_t>::max() / y)
        throw std::runtime_error("size overflow");
    return x * y;
}

struct Params {
    int r=0, c=0;
    u32 mod=0;
    std::string out;
    std::string algorithm="butterfly";
    bool verbose=false;
    double memory_gb=16.;
};

static Params parse(int argc, char** argv) {
    Params q;
    for (int i=1; i<argc; ++i) {
        std::string flag=argv[i];
        if (flag=="--verbose") {q.verbose=true; continue;}
        if (i+1==argc) throw std::runtime_error("missing value for " + flag);
        std::string val=argv[++i];
        if (flag=="--r") q.r=std::stoi(val);
        else if (flag=="--c") q.c=std::stoi(val);
        else if (flag=="--mod") q.mod=static_cast<u32>(std::stoul(val));
        else if (flag=="--out") q.out=val;
        else if (flag=="--algorithm") q.algorithm=val;
        else if (flag=="--memory-gb") q.memory_gb=std::stod(val);
        else throw std::runtime_error("unknown arg " + flag);
    }
    if (q.r<=0 || q.c<=0 || q.mod < 3 || q.mod>2147483647u || q.out.empty())
        throw std::runtime_error("usage: --r R --c C --mod PRIME --out MODFILE [--algorithm butterfly|naive] [--memory-gb LIMIT] [--verbose]");
    if (q.algorithm!="butterfly" && q.algorithm!="naive")
        throw std::runtime_error("algorithm must be butterfly or naive");
    if (q.r>q.c) std::swap(q.r,q.c);
    if (q.r>=24) throw std::runtime_error("row width >= 24 is outside prototype scope");
    if (q.memory_gb<=0) throw std::runtime_error("memory-gb must be positive");
    return q;
}

struct Block {
    int occmax, adjmax, stride;
    std::size_t state_size;
    std::vector<u32> coeff;
    Block(std::size_t masks, int o, int a, int padding):occmax(o),adjmax(a),stride(a+1+padding) {
        state_size=checked_product(static_cast<std::size_t>(o+1), static_cast<std::size_t>(stride));
        coeff.resize(checked_product(masks, state_size), 0);
    }
    u32* mask_ptr(std::size_t m) {return coeff.data()+m*state_size;}
    const u32* mask_ptr(std::size_t m) const {return coeff.data()+m*state_size;}
};

static std::vector<u32> compute(const Params& q) {
    const int width=q.r, height=q.c;
    const int nmask=1<<width;
    std::vector<int> occupancy(nmask), horiz(nmask);
    for (int m=0;m<nmask;++m) {
        occupancy[m]=__builtin_popcount(static_cast<unsigned>(m));
        horiz[m]=__builtin_popcount(static_cast<unsigned>(m & (m<<1)));
    }

    // The transform can increase the coupling degree by width. Padding is
    // included in each state's polynomial stride; no sparse maps or BigInts.
    Block prev(nmask,0,0,width);
    prev.coeff[0]=1;
    for (int h=0;h<height;++h) {
        auto t0=std::chrono::steady_clock::now();
        int nextO=(h+1)*width;
        int nextA=(h+1)*(width-1)+h*width;
        int pad=(h+1<height)?width:0;
        std::size_t bytes = prev.coeff.size()*sizeof(u32);
        std::size_t nextEntries=checked_product(static_cast<std::size_t>(nmask),
                                 checked_product(static_cast<std::size_t>(nextO+1), static_cast<std::size_t>(nextA+1+pad)));
        if ((static_cast<long double>(bytes)+static_cast<long double>(nextEntries)*sizeof(u32)) >
            q.memory_gb * 1024.0L*1024.0L*1024.0L)
            throw std::runtime_error("estimated two-layer RAM exceeds --memory-gb; no allocation attempted");
        Block next(nmask,nextO,nextA,pad);

        if (q.algorithm=="butterfly") {
            // Each bit performs the entire sum over whether that bit was
            // occupied in the previous row; masks are transformed in place.
            for (int bit=0; bit<width; ++bit) {
                int step=1<<bit;
                for (int block=0; block<nmask;block+=2*step) {
                    for (int off=0;off<step;++off) {
                        u32* f0=prev.mask_ptr(block+off);
                        u32* f1=prev.mask_ptr(block+off+step);
                        for (int o=0;o<=prev.occmax;++o) {
                            // In an h-row grid: every occupied vertex has
                            // degree <= 4, so couplings <= 2*o. Deleting
                            // (h*w-o) vertices destroys <= 4*(h*w-o)
                            // edges, giving the lower coupling bound.
                            // Each previously transformed bit raises only
                            // the upper bound by one (multiplication by y).
                            const int low=std::max(0,prev.adjmax-4*(prev.occmax-o));
                            const int high=std::min(prev.adjmax,2*o)+bit+1;
                            u32* a=f0+static_cast<std::size_t>(o)*prev.stride;
                            u32* b=f1+static_cast<std::size_t>(o)*prev.stride;
                            // Descending index preserves old b[j-1].
                            for (int j=high;j>=low;--j) {
                                u32 olda=a[j], oldb=b[j];
                                b[j]=addmod(olda, j>0?b[j-1]:0u, q.mod);
                                a[j]=addmod(olda,oldb,q.mod);
                            }
                        }
                    }
                }
            }
            // New-row occupancy and internal horizontal couplings are shifts;
            // each destination coefficient is written by exactly one source.
            for (int mask=0;mask<nmask;++mask) {
                const u32* src=prev.mask_ptr(mask);
                u32* dst=next.mask_ptr(mask);
                const int o_shift=occupancy[mask], a_shift=horiz[mask];
                for (int o=0;o<=prev.occmax;++o) {
                    const int low=std::max(0,prev.adjmax-4*(prev.occmax-o));
                    const int high=std::min(prev.adjmax,2*o)+width;
                    const u32* from=src+static_cast<std::size_t>(o)*prev.stride;
                    u32* to=dst+static_cast<std::size_t>(o+o_shift)*next.stride+a_shift;
                    std::copy_n(from+low,high-low+1,to+low);
                }
            }
        } else {
            // Reference dense conventional mask-pair DP for benchmarks / tests.
            for (int pmask=0;pmask<nmask;++pmask) {
                const u32* src=prev.mask_ptr(pmask);
                for (int mask=0;mask<nmask;++mask) {
                    int vo=occupancy[mask];
                    int va=horiz[mask]+__builtin_popcount(static_cast<unsigned>(pmask&mask));
                    u32* dst=next.mask_ptr(mask);
                    for (int o=0;o<=prev.occmax;++o) {
                        const u32* from=src+static_cast<std::size_t>(o)*prev.stride;
                        u32* to=dst+static_cast<std::size_t>(o+vo)*next.stride+va;
                        for (int a=0;a<=prev.adjmax;++a) {
                            to[a]=addmod(to[a],from[a],q.mod);
                        }
                    }
                }
            }
        }
        prev=std::move(next);
        if (q.verbose) {
            double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
            std::cerr << "row="<<(h+1)<<"/"<<height<<" width="<<width
                      <<" o_max="<<prev.occmax<<" a_max="<<prev.adjmax
                      <<" layer_MiB="<<(prev.coeff.size()*sizeof(u32)/1048576.0)
                      <<" sec="<<std::fixed<<std::setprecision(4)<<sec<<"\n";
        }
    }
    std::vector<u32> totals(checked_product(static_cast<std::size_t>(prev.occmax+1),
                              static_cast<std::size_t>(prev.adjmax+1)),0u);
    for (int m=0;m<nmask;++m) {
        const u32* src=prev.mask_ptr(m);
        for (int o=0;o<=prev.occmax;++o) {
            const u32* p=src+static_cast<std::size_t>(o)*prev.stride;
            u32* to=totals.data()+static_cast<std::size_t>(o)*(prev.adjmax+1);
            for (int a=0;a<=prev.adjmax;++a) to[a]=addmod(to[a],p[a],q.mod);
        }
    }
    return totals;
}

static void write_mod_file(const Params& p,const std::vector<u32>& counts) {
    const int omax=p.r*p.c;
    const int amax=2*p.r*p.c-p.r-p.c;
    if (counts.size()!=static_cast<std::size_t>(omax+1)*static_cast<std::size_t>(amax+1))
        throw std::runtime_error("unexpected final counts length");
    std::ofstream out(p.out,std::ios::binary);
    if (!out) throw std::runtime_error("cannot create "+p.out);
    const char magic[8]={'M','R','C','M','O','D','0','1'};
    out.write(magic,8);
    const u32 header[5]={static_cast<u32>(p.r),static_cast<u32>(p.c),p.mod,
                         static_cast<u32>(omax),static_cast<u32>(amax)};
    out.write(reinterpret_cast<const char*>(header),sizeof(header));
    out.write(reinterpret_cast<const char*>(counts.data()),counts.size()*sizeof(u32));
    if (!out) throw std::runtime_error("error while writing "+p.out);
}

int main(int argc,char** argv) {
    try {
        Params p=parse(argc,argv);
        const auto begin=std::chrono::steady_clock::now();
        auto counts=compute(p);
        write_mod_file(p,counts);
        double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
        std::cerr << "completed "<<p.r<<"x"<<p.c<<" mod="<<p.mod
                  <<" algorithm="<<p.algorithm<<" time_s="<<std::fixed<<std::setprecision(3)<<sec<<"\n";
    } catch (const std::exception& ex) {
        std::cerr << "ERROR: "<<ex.what()<<"\n";
        return 1;
    }
    return 0;
}
