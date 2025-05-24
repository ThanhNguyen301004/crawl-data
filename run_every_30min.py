import schedule
import time
import subprocess
import datetime

def job():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] Running crawler...")
    subprocess.run(["python", "main.py"])

job()

schedule.every(30).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)

