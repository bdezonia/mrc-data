import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class DPScheduler {

    static class Job implements Runnable {
        final int r, c;
        final File outDir;

        Job(int r, int c, File outDir) {
            this.r = r;
            this.c = c;
            this.outDir = outDir;
        }

        @Override
        public void run() {
            try {
                String base = r + "." + c;
                File doneFile  = new File(outDir, base + ".DONE");
                File outFile  = new File(outDir, base + ".csv");

                if (doneFile.exists()) {
                    System.out.println("SKIP " + base + " (DONE)");
                    return;
                }
                
                System.out.println("START " + base);

                var table = DP_optimized.compute_m_table(r, c, false);

                DP_optimized.write_table_csv(r, c, table, outFile.getPath());

                doneFile.createNewFile();
                
                System.out.println("FINISH " + base);

            } catch (Exception e) {
                System.err.println("ERROR on (" + r + "," + c + ")");
                e.printStackTrace();
            }
        }
    }

    public static void main(String[] args) throws Exception {
        
    	int rMax = 10;
        
    	int cMax = 20;
        
        int threads = Runtime.getRuntime().availableProcessors() - 3;

        if (threads < 1) threads = 1;

        File outDir = new File("results");

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--rMax": rMax = Integer.parseInt(args[++i]); break;
                case "--cMax": cMax = Integer.parseInt(args[++i]); break;
                case "--threads": threads = Integer.parseInt(args[++i]); break;
                case "--out": outDir = new File(args[++i]); break;
                default:
                    throw new IllegalArgumentException("Unknown arg: " + args[i]);
            }
        }

        if (!outDir.exists()) outDir.mkdirs();

        System.out.println("Using " + threads + " threads");
        System.out.println("Output dir: " + outDir.getAbsolutePath());

        ExecutorService pool = Executors.newFixedThreadPool(threads);

        for (int r = 1; r <= rMax; r++) {
            for (int c = r; c <= cMax; c++) {
                pool.execute(new Job(r, c, outDir));
            }
        }
        
        pool.shutdown();
        pool.awaitTermination(Long.MAX_VALUE, TimeUnit.DAYS);

        System.out.println("All jobs finished.");
    }
}
