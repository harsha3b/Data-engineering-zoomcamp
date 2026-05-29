import sys
import pandas as pd

print("arguments", sys.argv)
month = int(sys.argv[1])
print(f"Running pipeline for month {month}")
df=pd.DataFrame({'day': [1, 2, 3], 'passengers': [4, 5, 6]})
print(f"Displaying df before month column update for {month}:")
print(df.head())
print(f"Updating month column for {month}")
df['month']=month
print(df.head())
df.to_parquet(f"output_day_{sys.argv[1]}.parquet", index=False)
print('job completed')



