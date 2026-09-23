nice -n 10 java -Xmx8g -cp .:fastutil-8.5.18.jar DPScheduler \
  --rMax 35 \
  --cMax 35 \
  --threads 1 \
  --out ../data
