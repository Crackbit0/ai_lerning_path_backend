# Setting Up Persistent Database for AI Learning Path Generator

This guide explains how to set up a **free** PostgreSQL database so users can:
- Login from any device
- Sync their learning paths across devices
- Keep their progress saved permanently

## Quick Setup (5 minutes)

### Step 1: Create a Free Neon Database

1. Go to [Neon](https://neon.tech) and sign up (free)
2. Create a new project (e.g., "ai-learning-paths")
3. Copy the connection string (looks like: `postgresql://user:pass@host/db?sslmode=require`)

### Step 2: Add to HuggingFace Spaces Secrets

1. Go to your HuggingFace Space settings
2. Click on "Settings" → "Repository secrets"
3. Add a new secret:
   - **Name**: `DATABASE_URL`
   - **Value**: Your Neon connection string

### Step 3: Restart Your Space

The app will automatically create all needed tables on startup.

## Free Database Options

| Provider | Free Tier | Best For |
|----------|-----------|----------|
| [Neon](https://neon.tech) | 0.5GB, auto-suspend | Recommended - fastest |
| [Supabase](https://supabase.com) | 500MB, 50K requests | Good alternative |
| [CockroachDB](https://cockroachlabs.cloud) | 5GB | Distributed |

## Local Development

For local testing, you can either:

1. **Use SQLite (default)**: Just leave `DATABASE_URL` empty
2. **Use PostgreSQL**: Set `DATABASE_URL` in your `.env` file

## Verify Setup

After deployment, check the logs for:
```
DATABASE_URL is configured (using PostgreSQL for persistent storage)
✅ Database initialized
```

## Mobile App Configuration

The mobile app automatically syncs with the backend when users are logged in. Data is stored:
- **Logged-in users**: Server database (synced across devices)
- **Guest users**: Local device storage only

## Troubleshooting

### "Connection refused" errors
- Check if the connection string is correct
- Ensure `?sslmode=require` is at the end for Neon

### "Table doesn't exist" errors
- The app auto-creates tables on startup
- Restart the Space to re-run initialization

### Data not syncing
- Ensure user is logged in (not guest mode)
- Check network connectivity to the API
