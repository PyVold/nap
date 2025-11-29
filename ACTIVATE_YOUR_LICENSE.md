# How to Activate Your BICS License

## Step 1: Find Your License File

On your server (`npm@npm-pro:~/nap$`), run:

```bash
cd ~/nap
ls -la license_output/
```

You should see files like:
- `license_osama_YYYYMMDD_HHMMSS.txt` (your license file)
- `license_osama_YYYYMMDD_HHMMSS.json` (metadata)

## Step 2: View Your License Key

```bash
cat license_output/license_osama_*.txt
```

This will show your license details including the encrypted license key.

## Step 3: Activate the License

### Option A: Via Web UI (Easiest)

1. Open your browser and navigate to your NAP platform
2. Go to the **License** page (usually at `/license` or in Settings menu)
3. Copy the entire license key from the `.txt` file
4. Paste it into the activation form
5. Click **"Activate"**

### Option B: Via API (Command Line)

```bash
# Save your license key to a variable
LICENSE_KEY="gAAAAAB..."  # Copy the full key from your .txt file

# Activate via API
curl -X POST http://localhost:3000/api/license/activate \
  -H "Content-Type: application/json" \
  -d "{\"license_key\": \"$LICENSE_KEY\"}"
```

### Option C: Direct Database Activation (If services aren't running)

If your Docker containers or services aren't running, you can activate directly:

```bash
cd ~/nap

# Install required Python library
pip3 install sqlalchemy

# Run direct activation script
python3 activate_license_direct.py license_output/license_osama_*.txt
```

## Step 4: Verify Activation

Check the license status:

```bash
curl http://localhost:3000/api/license/status
```

You should see:
```json
{
  "valid": true,
  "tier": "enterprise",
  "tier_display": "Enterprise",
  "expires_at": "...",
  "days_until_expiry": 90,
  "is_active": true,
  ...
}
```

## Troubleshooting

### Issue: "No active license found" (404)
**Cause**: License hasn't been activated yet
**Solution**: Follow Step 3 to activate

### Issue: "License invalid or expired" (402)
**Cause**: Wrong encryption keys or expired license
**Solution**: Regenerate license with correct keys from your .env

### Issue: Services not running
**Check services**:
```bash
docker ps
# OR
docker-compose ps
```

**Start services**:
```bash
docker-compose up -d
```

### Issue: Can't access /license page
**Check if API is running**:
```bash
curl http://localhost:3000/api/health
```

If not responding, start the backend:
```bash
docker-compose up -d api-gateway
```

## Your License Details

Based on what you generated:
- **Customer**: BICS
- **Email**: osama.aboelfath@bics.com
- **Tier**: Enterprise
- **Duration**: 90 days
- **Max Devices**: 50
- **Max Users**: 10

## Next Steps

1. Find your license file: `ls license_output/`
2. Read the license key: `cat license_output/license_osama_*.txt`
3. Activate it via web UI or API
4. Verify it worked: `curl http://localhost:3000/api/license/status`

Once activated, you won't see the "expired or invalid license" error anymore! ✅
