#!/bin/bash
# Complete fix for admin dashboard access issue

echo "=========================================="
echo "Admin Dashboard Access Fix"
echo "=========================================="
echo ""

# Step 1: Check admin user's is_superuser status
echo "Step 1: Checking admin user status in database..."
RESULT=$(sudo docker compose exec -T database psql -U nap_user -d nap_db -t -c "SELECT username, role, is_superuser FROM users WHERE username = 'admin';")

echo "Current admin user status:"
echo "$RESULT"
echo ""

# Check if is_superuser is false
if echo "$RESULT" | grep -q "| f$"; then
    echo "⚠️  ISSUE FOUND: is_superuser is FALSE"
    echo ""
    echo "Step 2: Fixing admin user superuser status..."

    sudo docker compose exec -T database psql -U nap_user -d nap_db <<EOF
UPDATE users SET is_superuser = true WHERE username = 'admin';
SELECT username, role, is_superuser FROM users WHERE username = 'admin';
EOF

    echo ""
    echo "✅ Admin user is_superuser set to TRUE"
else
    echo "✅ Admin user already has is_superuser = TRUE"
fi

echo ""
echo "Step 3: Rebuilding admin-service and frontend with latest fixes..."
sudo docker compose build admin-service frontend

echo ""
echo "Step 4: Restarting services..."
sudo docker compose restart admin-service frontend

echo ""
echo "=========================================="
echo "Fix Complete!"
echo "=========================================="
echo ""
echo "IMPORTANT NEXT STEPS:"
echo "1. Open your browser"
echo "2. Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)"
echo "3. Or use Incognito/Private window"
echo "4. Go to http://192.168.1.150:8080"
echo "5. Logout if logged in"
echo "6. Login again with: admin / admin"
echo "7. Navigate to /admin"
echo ""
echo "The admin dashboard should now be accessible!"
