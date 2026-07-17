/**
 * T-2085: Organization member management UI
 *
 * Lists members, shows status (active/suspended), role, and allows:
 * - Suspending/reactivating users
 * - Changing role via existing PATCH /api/v1/admin/users/{user_id}/role
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface User {
  user_id: string;
  email: string;
  full_name: string | null;
  role: 'admin' | 'reviewer' | 'viewer';
  is_active: boolean;
  last_login: string | null;
}

interface ErrorState {
  message: string;
}

const ROLE_OPTIONS = ['admin', 'reviewer', 'viewer'] as const;

export default function OrgMemberManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorState | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [editingRole, setEditingRole] = useState<string | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/admin/users', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error('Failed to load users');
      }

      const data: User[] = await response.json();
      setUsers(data);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load users';
      setError({ message });
    } finally {
      setLoading(false);
    }
  }

  async function handleSuspendUser(userId: string) {
    try {
      setActionInProgress(userId);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/admin/users/${userId}/suspend`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to suspend user');
      }

      await loadUsers();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to suspend user';
      setError({ message });
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleReactivateUser(userId: string) {
    try {
      setActionInProgress(userId);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/admin/users/${userId}/reactivate`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to reactivate user');
      }

      await loadUsers();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reactivate user';
      setError({ message });
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleRoleChange(userId: string, newRole: string) {
    try {
      setActionInProgress(userId);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/admin/users/${userId}/role`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role: newRole }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update role');
      }

      setEditingRole(null);
      await loadUsers();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update role';
      setError({ message });
    } finally {
      setActionInProgress(null);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading members...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Organization Members</h1>
          <p className="mt-1 text-gray-600">Manage user roles and access</p>
        </div>
        <Link
          href="/admin/members/import"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Bulk Import
        </Link>
      </div>

      {error && (
        <div role="alert" className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error.message}</p>
        </div>
      )}

      {users.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No members found</p>
        </div>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Name
                </th>
                <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Email
                </th>
                <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Role
                </th>
                <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Last Login
                </th>
                <th scope="col" className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.user_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{user.full_name || 'N/A'}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-gray-700">{user.email}</div>
                  </td>
                  <td className="px-6 py-4">
                    {editingRole === user.user_id ? (
                      <select
                        aria-label={`Role for ${user.full_name || user.email}`}
                        value={users.find((u) => u.user_id === user.user_id)?.role || 'viewer'}
                        onChange={(e) => {
                          handleRoleChange(user.user_id, e.target.value);
                        }}
                        disabled={actionInProgress === user.user_id}
                        className="px-2 py-1 border border-gray-300 rounded text-sm"
                      >
                        {ROLE_OPTIONS.map((role) => (
                          <option key={role} value={role}>
                            {role.charAt(0).toUpperCase() + role.slice(1)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                          user.role === 'admin'
                            ? 'bg-purple-100 text-purple-800'
                            : user.role === 'reviewer'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                        user.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {user.is_active ? 'Active' : 'Suspended'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-600">
                      {user.last_login
                        ? new Date(user.last_login).toLocaleDateString()
                        : 'Never'}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button
                      onClick={() => setEditingRole(editingRole === user.user_id ? null : user.user_id)}
                      disabled={actionInProgress === user.user_id}
                      className="text-sm px-3 py-1 text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                    >
                      {editingRole === user.user_id ? 'Cancel' : 'Edit Role'}
                    </button>
                    {user.is_active ? (
                      <button
                        onClick={() => handleSuspendUser(user.user_id)}
                        disabled={actionInProgress === user.user_id}
                        className="text-sm px-3 py-1 text-red-600 hover:text-red-800 disabled:text-gray-400"
                      >
                        Suspend
                      </button>
                    ) : (
                      <button
                        onClick={() => handleReactivateUser(user.user_id)}
                        disabled={actionInProgress === user.user_id}
                        className="text-sm px-3 py-1 text-green-600 hover:text-green-800 disabled:text-gray-400"
                      >
                        Reactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
