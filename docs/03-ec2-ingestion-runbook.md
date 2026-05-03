# EC2 Ingestion Runbook

This runbook is the safer way to collect AIS and daily snapshot data for 14 days on AWS EC2 without depending on your laptop staying online.

The key idea is simple: once the process is started on the EC2 instance as a `systemd` service, your local Wi-Fi, closed laptop, SSH disconnects, or terminal crashes do not stop the ingestion job. The work keeps running on the remote machine until the EC2 instance stops, the service is stopped, or the process fails repeatedly.

## Why This Is Better Than `tmux`

`tmux` is useful for interactive sessions, but it is not the best control plane for a 14-day unattended ingestion run.

With `systemd`:

- the AIS process keeps running after SSH disconnects
- the service can restart automatically after transient crashes
- the service comes back after an EC2 reboot if enabled
- daily jobs can run via `systemd` timers with `Persistent=true`
- you can inspect logs with `journalctl` instead of depending on one terminal session

## What Local Problems Will Not Stop The Job

The following should not terminate ingestion once the service is running on EC2:

- your laptop goes to sleep
- your local network drops
- your SSH session disconnects
- you close your terminal
- you shut down your local machine

## What Can Still Stop The Job

This setup is more resilient, not magic. Ingestion can still stop if:

- the EC2 instance is stopped or terminated
- AWS credentials on the instance are invalid and S3 writes fail permanently
- the disk fills up
- the process crashes continuously and never stabilizes
- you stop the service manually

## 1. Provision The EC2 Instance

From your local machine:

```bash
cd /Users/loicns/Projects/data-party-logistics
bash infra/provision_server.sh
```

If the script prints:

```text
Permission denied
```

while writing `~/.ssh/dpl-ingestion-key.pem`, the usual cause is that the key file already exists locally with restrictive permissions such as `0400`. The updated script now handles that case by reusing the existing key instead of trying to overwrite it.

Behavior to expect now:

- if `~/.ssh/dpl-ingestion-key.pem` already exists and the AWS key pair `dpl-ingestion-key` also exists, the script reuses both
- if the local PEM exists but the AWS key pair does not, the script stops and tells you to recreate the pair
- if the AWS key pair exists but the local PEM is missing, the script stops because AWS cannot return the private key again after creation

If you are in the third case, clean up the AWS key pair and rerun:

```bash
aws ec2 delete-key-pair --key-name dpl-ingestion-key --profile dpl --region eu-west-3
rm -f ~/.ssh/dpl-ingestion-key.pem
bash infra/provision_server.sh
```

Then connect with the command printed by the script:

```bash
ssh -i ~/.ssh/dpl-ingestion-key.pem ubuntu@<YOUR_PUBLIC_IP>
```

## 2. Bootstrap The Runtime On EC2

This repo currently targets Python `3.12`, so do not rely on the default Ubuntu Python alone.

Run this on the EC2 instance:

```bash
sudo apt update
sudo apt install -y curl git ca-certificates

curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

git clone https://github.com/<your-username>/data-party-logistics.git
cd /home/ubuntu/data-party-logistics

uv python install 3.12
uv sync --python 3.12
cp .env.example .env
```

Edit `.env` on the server and fill in the real values:

```bash
nano /home/ubuntu/data-party-logistics/.env
```

At minimum, make sure these are set correctly:

- `AISSTREAM_API_KEY`
- `S3_BUCKET_RAW`
- `AWS_REGION=eu-west-3`
- `AWS_PROFILE=dpl` only if you will use an AWS CLI profile on the instance

## 3. Make Sure AWS Credentials Exist On The EC2 Host

The ingestion code writes directly to S3 with `boto3`, so the EC2 machine itself must have AWS credentials.

Best practice:

- attach an IAM instance role with S3 write access to the raw bucket

Acceptable fallback:

- install AWS CLI on the EC2 instance if needed: `sudo apt install -y awscli`
- run `aws configure --profile dpl` on the EC2 instance
- or copy the needed AWS credential/config files into `~/.aws/`

If you use an IAM instance role instead of a local profile, remove `AWS_PROFILE` from `/home/ubuntu/data-party-logistics/.env` so `boto3` can use the instance role provider chain directly.

If the EC2 box cannot authenticate to AWS, local disconnection is not the problem; S3 writes will fail on the server.

## 4. Install `systemd` Units

Create the long-running AIS service:

```bash
sudo tee /etc/systemd/system/dpl-ais-stream.service > /dev/null <<'EOF'
[Unit]
Description=Data Party Logistics AIS stream ingestion
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/data-party-logistics
EnvironmentFile=/home/ubuntu/data-party-logistics/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/.local/bin/uv run python -m ingestion.clients.ais_stream
Restart=always
RestartSec=30
KillSignal=SIGTERM
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
EOF
```

Create the daily weather snapshot service:

```bash
sudo tee /etc/systemd/system/dpl-weather.service > /dev/null <<'EOF'
[Unit]
Description=Data Party Logistics weather ingestion
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/data-party-logistics
EnvironmentFile=/home/ubuntu/data-party-logistics/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/.local/bin/uv run python -m ingestion.clients.weather
EOF
```

Create the daily weather timer:

```bash
sudo tee /etc/systemd/system/dpl-weather.timer > /dev/null <<'EOF'
[Unit]
Description=Run Data Party Logistics weather ingestion daily

[Timer]
OnCalendar=*-*-* 02:00:00 UTC
Persistent=true
Unit=dpl-weather.service

[Install]
WantedBy=timers.target
EOF
```

Create the daily NOAA tides service:

```bash
sudo tee /etc/systemd/system/dpl-noaa-tides.service > /dev/null <<'EOF'
[Unit]
Description=Data Party Logistics NOAA tides ingestion
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/data-party-logistics
EnvironmentFile=/home/ubuntu/data-party-logistics/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/.local/bin/uv run python -m ingestion.clients.noaa_tides
EOF
```

Create the daily NOAA tides timer:

```bash
sudo tee /etc/systemd/system/dpl-noaa-tides.timer > /dev/null <<'EOF'
[Unit]
Description=Run Data Party Logistics NOAA tides ingestion daily

[Timer]
OnCalendar=*-*-* 02:10:00 UTC
Persistent=true
Unit=dpl-noaa-tides.service

[Install]
WantedBy=timers.target
EOF
```

## 5. Start The Services And Schedule The 14-Day Stop

Reload `systemd`, start the long-running stream, and enable the daily timers:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dpl-ais-stream.service
sudo systemctl enable --now dpl-weather.timer
sudo systemctl enable --now dpl-noaa-tides.timer
```

Schedule a stop exactly 14 days from the moment you launch it:

```bash
STOP_AT="$(date -u -d '+14 days' '+%Y-%m-%d %H:%M:%S UTC')"
echo "$STOP_AT"

sudo systemd-run \
  --unit dpl-stop-ais \
  --on-calendar "$STOP_AT" \
  /bin/systemctl stop dpl-ais-stream.service
```

This is the important difference from running the job inside your laptop shell: the stop event is scheduled on the EC2 instance itself.

## 6. Verify That Everything Is Running

Use these commands on the EC2 instance:

```bash
sudo systemctl status dpl-ais-stream.service --no-pager
sudo systemctl status dpl-weather.timer --no-pager
sudo systemctl status dpl-noaa-tides.timer --no-pager
sudo systemctl status dpl-stop-ais.timer --no-pager
```

Live logs:

```bash
sudo journalctl -u dpl-ais-stream.service -f
```

Recent timer history:

```bash
systemctl list-timers --all | grep dpl
```

At this point you can disconnect from SSH. The ingestion keeps running on EC2.

## 7. Daily Operations

Useful commands:

```bash
sudo systemctl restart dpl-ais-stream.service
sudo systemctl stop dpl-ais-stream.service
sudo systemctl start dpl-ais-stream.service
sudo journalctl -u dpl-weather.service -n 100 --no-pager
sudo journalctl -u dpl-noaa-tides.service -n 100 --no-pager
```

## 8. Warehouse Load Note

This repo currently does not contain a committed source file at `ingestion/loaders/s3_to_postgres.py`, so this runbook does not schedule that job.

Once a real load entrypoint exists in source control, add it as another `oneshot` service plus timer using the same pattern as weather and NOAA tides.

## 9. Shut Everything Down And Clean Up

To stop the jobs on the EC2 instance:

```bash
sudo systemctl disable --now dpl-ais-stream.service
sudo systemctl disable --now dpl-weather.timer
sudo systemctl disable --now dpl-noaa-tides.timer
```

To terminate the instance from your local machine later:

```bash
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" "Name=key-name,Values=dpl-ingestion-key" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text \
  --profile dpl \
  --region eu-west-3)

aws ec2 terminate-instances \
  --instance-ids "$INSTANCE_ID" \
  --profile dpl \
  --region eu-west-3
```

If you also want to remove the security group, key pair, and local key file:

```bash
aws ec2 delete-security-group --group-name dpl-ingestion-sg --profile dpl --region eu-west-3
aws ec2 delete-key-pair --key-name dpl-ingestion-key --profile dpl --region eu-west-3
rm -f ~/.ssh/dpl-ingestion-key.pem
```
