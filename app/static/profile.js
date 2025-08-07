function renderCurrentUser(user) {
const tableBody = document.getElementById("profile-table-body");

if (!user) {
    tableBody.innerHTML = `
    <tr>
        <td colspan="3" class="text-center py-5">
        <i class="bi bi-person-slash fs-1 text-muted mb-3"></i>
        <h4 class="text-muted">No User Logged In</h4>
        <p class="text-muted">Log in to see your profile information.</p>
        </td>
    </tr>
    `;
    return;
}

const createdAt = new Date(user.created_at).toLocaleDateString();

tableBody.innerHTML = `
    <tr data-user-id="${user.user_id}">
    <td>
        <strong>${user.username}</strong>
    </td>
    <td>
        <small>${createdAt}</small>
    </td>
    <td>
        <div class="d-flex gap-1">
        <button class="btn btn-sm btn-outline-success" onclick="logoutUser(); return false;" title="Logout">
            <i class="bi bi-box-arrow-right"></i>
        </button>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.user_id}, '${user.username}'); return false;" title="Delete User">
            <i class="bi bi-trash"></i>
        </button>
        </div>
    </td>
    </tr>
`;
}

async function logoutUser() {
    fetch('/api/users/logout', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(res => {
        if (res.ok) {
            // redirect user to participants page
            window.location.href = '/';
        } else {
            return res.json().then(data => {
                console.error("Logout failed:", data);
                alert("Logout failed.");
            });
        }
    })
    .catch(error => {
        console.error("Error logging out:", error);
        alert("An error occurred during logout.");
    });
}

async function deleteUser(userId) {
    if (!confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
      return;
    }
  
    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
  
      if (response.ok) {
        alert("Your account has been deleted.");
        // Redirect after deletion, e.g., to homepage or login page
        window.location.href = '/';
      } else {
        const errorData = await response.json();
        alert("Error deleting user: " + (errorData.error || "Unknown error"));
      }
    } catch (error) {
      console.error("Delete user failed:", error);
      alert("An error occurred while deleting the account.");
    }
  }
  

fetch('/api/users/current')
    .then(res => res.json())
    .then(user => {
    renderCurrentUser(user);
    })
    .catch(error => {
    console.error("Error loading current user:", error);
    });

window.logoutUser = logoutUser;
window.deleteUser = deleteUser;
