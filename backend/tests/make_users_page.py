
import re

with open('admin-users.php', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the top PHP calculation block 
# It goes from `$stats = [];` down to `?>` just before `<!DOCTYPE html>`
php_block_pattern = r'\$stats = \[\];.*?\?>'
new_php_block = """$users = [];
$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    
    if ($action === 'toggle_role') {
        $user_id = $_POST['user_id'] ?? '';
        $new_role = $_POST['new_role'] ?? '';
        $response = $API->put('/api/v1/admin/users/' . $user_id . '/role', ['role' => $new_role], $token);
        if ($response['success']) {
            $success = "User role updated successfully.";
        } else {
            $error = $response['message'] ?? "Failed to update role.";
        }
    } elseif ($action === 'delete_user') {
        $user_id = $_POST['user_id'] ?? '';
        $response = $API->delete('/api/v1/admin/users/' . $user_id, $token);
        if ($response['success']) {
            $success = "User deleted successfully.";
        } else {
            $error = $response['message'] ?? "Failed to delete user.";
        }
    }
}

$response = $API->get('/api/v1/admin/users', $token);
if ($response['success']) {
    $users = $response['data'] ?? [];
}

$products = [];
$lowStock = 0;
$newOrderCount = 0;

$adminCount = 0;
foreach($users as $u) {
    if(($u['role'] ?? '') === 'admin') $adminCount++;
}
$customerCount = count($users) - $adminCount;
?>"""
html = re.sub(php_block_pattern, new_php_block, html, flags=re.DOTALL)

# Let's fix the sidebar so "Overview" is not active, but a new "Users" is active.
nav_pattern = r'<a class="sb-item on" href="admin-dashboard\.php">'
html = html.replace(nav_pattern, '<a class="sb-item" href="admin-dashboard.php">')

users_nav_html = """      <a class="sb-item on" href="admin-users.php">
        <i class="fa-solid fa-users"></i> Users
      </a>"""

# Insert the Users menu item after Dashboard
html = html.replace('<a class="sb-item" href="admin-home-banner.php">', users_nav_html + '\n      <a class="sb-item" href="admin-home-banner.php">')

# Replace topbar overview breadcrumb
html = html.replace('<span class="cur">Overview</span>', '<span class="cur">Manage Users</span>')

# Replace the content area inside <div class="content"> ... </div>
# The content area is everything after `<!-- Content -->\n  <div class="content">` up until the first script block or closing body tag.
content_pattern = r'<!-- Content -->\s*<div class="content">.*?</div>\s*</div>\s*(?:<!-- 모달|<!-- modals|</body>)'

new_content = """<!-- Content -->
  <div class="content">

    <!-- Alerts -->
    <?php if ($error): ?>
      <div class="alert alert-error"><i class="fa-solid fa-circle-exclamation"></i> <?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>
    <?php if ($success): ?>
      <div class="alert alert-success"><i class="fa-solid fa-circle-check"></i> <?php echo htmlspecialchars($success); ?></div>
    <?php endif; ?>

    <!-- Page Header -->
    <div class="ph">
      <div>
        <h1>Manage Users</h1>
        <p>View, promote, or delete registered website accounts</p>
      </div>
    </div>

    <!-- KPIs -->
    <div class="kpi-row" style="grid-template-columns: 1fr 1fr 1fr;">
      <div class="kpi">
        <div class="kpi-icon"><i class="fa-solid fa-users"></i></div>
        <div class="kpi-lbl">Total Users</div>
        <div class="kpi-val"><?php echo count($users); ?></div>
        <div class="kpi-sub">Total registered accounts</div>
      </div>
      <div class="kpi">
        <div class="kpi-icon"><i class="fa-solid fa-user-shield"></i></div>
        <div class="kpi-lbl">Administrators</div>
        <div class="kpi-val"><?php echo $adminCount; ?></div>
        <div class="kpi-sub"><span style="color:var(--grn);">Staff members</span></div>
      </div>
      <div class="kpi">
        <div class="kpi-icon"><i class="fa-solid fa-user"></i></div>
        <div class="kpi-lbl">Customers</div>
        <div class="kpi-val"><?php echo $customerCount; ?></div>
        <div class="kpi-sub">Regular shoppers</div>
      </div>
    </div>

    <!-- Users Table Card -->
    <div class="card" style="margin-top:22px;">
      <div class="card-hd">
        <div class="card-ttl"><i class="fa-solid fa-list-ul"></i> Registered Users</div>
      </div>
      <div class="card-bd-0" style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Joined</th>
              <th style="text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <?php foreach($users as $u): ?>
              <tr>
                <td>
                  <div class="prod-cell">
                    <div class="sb-avatar" style="width:36px; height:36px; border-radius:5px; font-size:1rem;"><?php echo strtoupper(substr($u['name'] ?? 'U', 0, 1)); ?></div>
                    <div>
                      <div class="prod-name"><?php echo htmlspecialchars($u['name'] ?? 'Unknown'); ?></div>
                      <div class="prod-sub font-mono">ID: <?php echo substr($u['_id'] ?? '...', -6); ?></div>
                    </div>
                  </div>
                </td>
                <td><div style="font-size:0.8rem;"><?php echo htmlspecialchars($u['email'] ?? ''); ?></div></td>
                <td>
                  <?php if(($u['role'] ?? '') === 'admin'): ?>
                    <span class="pill p-blu"><i class="fa-solid fa-shield"></i> Admin</span>
                  <?php else: ?>
                    <span class="pill p-gray">User</span>
                  <?php endif; ?>
                </td>
                <td>
                  <div style="font-size:0.77rem; color:var(--t2);">
                    <?php echo isset($u['createdAt']) ? date('M d, Y', strtotime($u['createdAt'])) : '—'; ?>
                  </div>
                </td>
                <td style="text-align:right;">
                  <form method="POST" style="display:inline-block; margin-right:4px;">
                    <input type="hidden" name="action" value="toggle_role">
                    <input type="hidden" name="user_id" value="<?php echo $u['_id']; ?>">
                    <input type="hidden" name="new_role" value="<?php echo ($u['role'] ?? '') === 'admin' ? 'user' : 'admin'; ?>">
                    <button type="submit" class="btn btn-out btn-xs" title="<?php echo ($u['role'] ?? '') === 'admin' ? 'Demote to User' : 'Promote to Admin'; ?>" <?php if($u['_id'] === $user['_id']) echo "disabled style='opacity:0.5;cursor:not-allowed;'"; ?>>
                      <i class="fa-solid <?php echo ($u['role'] ?? '') === 'admin' ? 'fa-arrow-down' : 'fa-arrow-up'; ?>"></i>
                    </button>
                  </form>
                  <form method="POST" style="display:inline-block;" onsubmit="return confirm('Are you sure you want to delete this user? This cannot be undone.');">
                    <input type="hidden" name="action" value="delete_user">
                    <input type="hidden" name="user_id" value="<?php echo $u['_id']; ?>">
                    <button type="submit" class="btn btn-red btn-xs" title="Delete User" <?php if($u['_id'] === $user['_id']) echo "disabled style='opacity:0.5;cursor:not-allowed;'"; ?>>
                      <i class="fa-solid fa-trash-can"></i>
                    </button>
                  </form>
                </td>
              </tr>
            <?php endforeach; ?>
            <?php if(empty($users)): ?>
              <tr>
                <td colspan="5" style="text-align:center; padding:30px; color:var(--t3); font-size:0.85rem;">No users found.</td>
              </tr>
            <?php endif; ?>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
<!-- Modals would go here if any -->
</body>
"""
html_parts = html.split('<!-- Content -->')
top_part = html_parts[0]
bottom_part = html_parts[1]
# We want to discard everything in bottom_part up to </body>
if '</body>' in bottom_part:
    _, end_part = bottom_part.rsplit('</body>', 1)
else:
    end_part = ""

final_html = top_part + new_content + "\n</html>"

with open('admin-users.php', 'w', encoding='utf-8') as f:
    f.write(final_html)
print("admin-users.php has been completely generated.")

