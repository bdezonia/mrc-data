nice -n 10 java -Xmx8g -cp .:fastutil-8.5.18.jar DPScheduler \
  --rMax 30 \
  --cMax 30 \
  --threads 1 \
  --out ../data
