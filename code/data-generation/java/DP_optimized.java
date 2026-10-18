import java.io.*;
import java.math.BigInteger;
import java.util.Arrays;

import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2ObjectMap;

/**
 * Drop-in style Java port of DP_optimized.py core:
 * - compute_m_table(r,c) exact (BigInteger)
 * - dense CSV writer with .DONE. sentinel
 * - resume log support
 *
 * Requires fastutil:
 *   it.unimi.dsi:fastutil
 */
public class DP_optimized {

    // ------------------------------------------------------------
    // Utility
    // ------------------------------------------------------------
    private static int popcount(int x) {
        return Integer.bitCount(x);
    }

    // horizontal adjacencies within a row-mask
    private static int horizAdj(int mask) {
        return popcount(mask & (mask << 1));
    }

    // ------------------------------------------------------------
    // Core DP (one row extension)
    // dpPrev[t] : Int2ObjectMap<BigInteger> from packed_key -> count
    // packed_key = o*Amax + a
    // ------------------------------------------------------------
    private static Int2ObjectOpenHashMap<BigInteger>[] extendDp(
            Int2ObjectOpenHashMap<BigInteger>[] dpPrev,
            int width,
            int cellsK,
            int edgesK,
            int Amax_arg,
            int[] occ_arg,
            int[] horiz_arg,
            boolean verboseRowStats)
    {
        final int Amax = Amax_arg;
        final int[] occ = occ_arg;
        final int[] horiz = horiz_arg;
        
        if (width >= 31) {
            throw new IllegalArgumentException("Width too large: " + width);
        }
        
        final int numStates = 1 << width;

        @SuppressWarnings("unchecked")
        Int2ObjectOpenHashMap<BigInteger>[] dpNext = new Int2ObjectOpenHashMap[numStates];

        int[] vertT = new int[numStates];
        for (int t = 0; t < numStates; t++) {
            Int2ObjectOpenHashMap<BigInteger> oaMap = dpPrev[t];
            if (oaMap == null || oaMap.isEmpty()) continue;
            
            for (int s = 0; s < numStates; s++) {
                vertT[s] = popcount(t & s);
            }
            
            // iterate next-row masks
            for (int s = 0; s < numStates; s++) {
                final int oS = occ[s];
                // aS = horiz within new row + vertical adj with previous row
                final int aS = horiz[s] + vertT[s];

                if (dpNext[s] == null) {
                    
                    dpNext[s] = new Int2ObjectOpenHashMap<BigInteger>();
                    dpNext[s].defaultReturnValue(null);
                }

                Int2ObjectOpenHashMap<BigInteger> outMap = dpNext[s];
                
                for (Int2ObjectMap.Entry<BigInteger> e : oaMap.int2ObjectEntrySet()) {
                    final int key = e.getIntKey();
                    final BigInteger cnt = e.getValue();

                    final int o = key / Amax;
                    final int a = key - o * Amax;

                    final int no = o + oS;
                    final int na = a + aS;

                    if (no <= cellsK && na <= edgesK) {
                        final int newKey = no * Amax + na;
                        BigInteger prev = outMap.get(newKey);
                        if (prev == null) {
                            outMap.put(newKey, cnt);
                        } else {
                            outMap.put(newKey, prev.add(cnt));
                        }
                    }
                }
            }
        }

        return dpNext;
    }

    // ------------------------------------------------------------
    // compute_m_table(r,c): returns final table as packed_key -> count
    // packed_key = o*Amax + a, where Amax = totalEdges+1
    // ------------------------------------------------------------
    public static
    
    	Int2ObjectOpenHashMap<BigInteger>
    
    		compute_m_table(int r, int c, boolean verbose)
    {
        // symmetry: ensure r <= c (width = r)
        if (r > c) {
            int tmp = r; r = c; c = tmp;
        }

        final int width = r;
        final int height = c;

        final int totalCells = r * c;
        final int totalEdges = r * (c - 1) + c * (r - 1);
        final int Amax = totalEdges + 1;

        final int numStates = 1 << width;

        // precompute per-mask stats
        final int[] occ = new int[numStates];
        final int[] horiz = new int[numStates];
        for (int m = 0; m < numStates; m++) {
            occ[m] = popcount(m);
            horiz[m] = horizAdj(m);
        }

        // dpPrev[t] is a sparse map from packed_key -> BigInteger count
        @SuppressWarnings("unchecked")
        Int2ObjectOpenHashMap<BigInteger>[] dpPrev = new Int2ObjectOpenHashMap[numStates];

        // initial: before processing any rows, prev_mask = 0 with (o=0,a=0) count=1
        dpPrev[0] = new Int2ObjectOpenHashMap<BigInteger>();
        dpPrev[0].defaultReturnValue(null);
        dpPrev[0].put(0, BigInteger.ONE);

        // main DP: rows 0 .. height-1
        for (int k = 0; k < height; k++) {
            int cellsK = (k + 1) * width;
            int edgesK = (k + 1) * (width - 1) + k * width;

            dpPrev = extendDp(dpPrev, width, cellsK, edgesK, Amax, occ, horiz, false);

            if (verbose) {
                int active = 0;
                long totalKeys = 0;
                for (int t = 0; t < numStates; t++) {
                    if (dpPrev[t] != null && !dpPrev[t].isEmpty()) {
                        active++;
                        totalKeys += dpPrev[t].size();
                    }
                }
                System.out.println("Row " + (k + 1) + "/" + height +
                        ": active masks=" + active + ", total keys=" + totalKeys);
            }
        }

        // aggregate over last mask
        Int2ObjectOpenHashMap<BigInteger> result = new Int2ObjectOpenHashMap<BigInteger>();
        result.defaultReturnValue(null);

        for (int t = 0; t < numStates; t++) {
            Int2ObjectOpenHashMap<BigInteger> m = dpPrev[t];
            if (m == null || m.isEmpty()) continue;

            for (Int2ObjectMap.Entry<BigInteger> e : m.int2ObjectEntrySet()) {
                int key = e.getIntKey();
                BigInteger cnt = e.getValue();
                BigInteger prev = result.get(key);
                if (prev == null) result.put(key, cnt);
                else result.put(key, prev.add(cnt));
            }
        }

        return result;
    }

    // ------------------------------------------------------------
    // Dense CSV writer with .DONE. sentinel
    // ------------------------------------------------------------
    public static void write_table_csv(
            int r,
            int c,
            Int2ObjectOpenHashMap<BigInteger> table,
            String outFilePath
    ) throws IOException {
        final int maxO = r * c;
        final int maxA = 2 * r * c - r - c;

        // totalEdges for Amax to decode packed keys
        final int totalEdges = r * (c - 1) + c * (r - 1);
        final int Amax = totalEdges + 1;

        try (BufferedWriter bw = new BufferedWriter(new FileWriter(outFilePath))) {
            bw.write("r,c,o,a,count\n");

            for (int o = 0; o <= maxO; o++) {
                int base = o * Amax;
                for (int a = 0; a <= maxA; a++) {
                    int key = base + a;
                    BigInteger cnt = table.get(key);
                    if (cnt == null) cnt = BigInteger.ZERO;
                    bw.write(r + "," + c + "," + o + "," + a + "," + cnt.toString());
                    bw.write("\n");
                }
            }

            bw.write(".DONE.\n");
        }
    }

    // ------------------------------------------------------------
    // Simple CLI compatible with your Python style
    // ------------------------------------------------------------
    public static void main(String[] args) throws Exception {
        int r = -1, c = -1;
        String out = null;
        boolean verbose = false;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--r":
                    r = Integer.parseInt(args[++i]);
                    break;
                case "--c":
                    c = Integer.parseInt(args[++i]);
                    break;
                case "--out":
                    out = args[++i];
                    break;
                case "--verbose":
                    verbose = true;
                    break;
                default:
                    throw new IllegalArgumentException("Unknown arg: " + args[i]);
            }
        }

        if (r < 1 || c < 1 || out == null) {
            throw new IllegalArgumentException("Usage: --r <int> --c <int> --out <file> [--resume <file>] [--verbose]");
        }

        Int2ObjectOpenHashMap<BigInteger> table = compute_m_table(r, c, verbose);
        
        write_table_csv(r, c, table, out);
    }
}
