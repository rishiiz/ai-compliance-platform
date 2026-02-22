"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/contexts/auth-context";
import { FileText, Users, Database, UserPlus, Trash2, User } from "lucide-react";
import { config } from "@/lib/env";
import {
  connectDatabase,
  fetchDatabaseStatus,
  getSettings,
  updateSettings,
  fetchUsers,
  createUser,
  setUserPassword,
  deleteUser,
} from "@/api";

function ProfileCard({ user }: { user: { name: string; email: string; role: string; department: string } }) {
  const initials = user.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
  const roleLabel =
    user.role === "admin" ? "Admin" : user.role === "compliance" ? "Compliance Officer" : "Viewer";

  return (
    <Card className="bg-card/80 backdrop-blur border-border/80">
      <CardContent className="p-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <Avatar className="h-20 w-20 ring-2 ring-primary/30 ring-offset-2 ring-offset-background">
            <AvatarFallback className="text-xl bg-primary/20 text-primary font-semibold">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 space-y-2">
            <h2 className="text-xl font-semibold">{user.name}</h2>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            <div className="flex flex-wrap gap-2 pt-1">
              <Badge variant="secondary">{roleLabel}</Badge>
              {user.department && <Badge variant="outline">{user.department}</Badge>}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { user, isAdmin } = useAuth();
  const searchParams = useSearchParams();
  const defaultTab = searchParams.get("tab") ?? "database";

  // Database (connect to any DB via credentials: PostgreSQL, MySQL, etc.)
  const [dbHost, setDbHost] = useState("");
  const [dbPort, setDbPort] = useState<string>("5432");
  const [dbDialect, setDbDialect] = useState<"postgresql" | "mysql">("postgresql");
  const [dbUsername, setDbUsername] = useState("");
  const [dbPassword, setDbPassword] = useState("");
  const [dbName, setDbName] = useState("");
  const [dbConnected, setDbConnected] = useState(false);
  const [dbConnecting, setDbConnecting] = useState(false);
  const [dbMessage, setDbMessage] = useState<string | null>(null);
  const [dbError, setDbError] = useState<string | null>(null);

  // Policy settings
  const [confidence, setConfidence] = useState(85);
  const [maxFileSizeMb, setMaxFileSizeMb] = useState(10);
  const [maxUploadsPerHour, setMaxUploadsPerHour] = useState(30);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(true);

  // Users
  const [usersList, setUsersList] = useState<Array<{ id: number; email: string; name: string; role: string; department: string }>>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [addUserOpen, setAddUserOpen] = useState(false);
  const [addUserEmail, setAddUserEmail] = useState("");
  const [addUserName, setAddUserName] = useState("");
  const [addUserRole, setAddUserRole] = useState("Compliance Officer");
  const [addUserDept, setAddUserDept] = useState("");
  const [addUserPassword, setAddUserPassword] = useState("");
  const [addUserSubmitting, setAddUserSubmitting] = useState(false);
  const [addUserError, setAddUserError] = useState<string | null>(null);
  const [setPasswordUserId, setSetPasswordUserId] = useState<number | null>(null);
  const [setPasswordValue, setSetPasswordValue] = useState("");
  const [setPasswordSubmitting, setSetPasswordSubmitting] = useState(false);
  const [setPasswordError, setSetPasswordError] = useState<string | null>(null);
  const [deleteConfirmUser, setDeleteConfirmUser] = useState<{ id: number; name: string; email: string } | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    if (!config.apiUrl) { setSettingsLoading(false); return; }
    setSettingsLoading(true);
    try {
      const s = await getSettings();
      if (s.confidence_threshold) setConfidence(Number(s.confidence_threshold) || 85);
      if ("policy_upload_max_file_size_mb" in s) setMaxFileSizeMb(Math.max(1, Number(s.policy_upload_max_file_size_mb) || 50));
      if ("policy_upload_max_per_hour" in s) setMaxUploadsPerHour(Math.max(0, Number(s.policy_upload_max_per_hour) || 0));
      const status = await fetchDatabaseStatus();
      setDbConnected(status.connected);
      if (status.host) setDbHost(status.host);
      if (status.port) setDbPort(status.port);
      if (status.dialect === "mysql" || status.dialect === "postgresql") setDbDialect(status.dialect);
      if (status.username) setDbUsername(status.username);
      if (status.db_name) setDbName(status.db_name);
    } finally {
      setSettingsLoading(false);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    if (!config.apiUrl) return;
    setUsersLoading(true);
    try {
      const list = await fetchUsers();
      setUsersList(list);
    } finally {
      setUsersLoading(false);
    }
  }, []);

  useEffect(() => { if (isAdmin) { loadSettings(); loadUsers(); } }, [isAdmin, loadSettings, loadUsers]);

  if (!user) return null;

  // Non-admin: profile card only
  if (!isAdmin) {
    return (
      <PageTransition>
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
            <p className="mt-1 text-muted-foreground">Your profile</p>
          </div>
          <ProfileCard user={user} />
        </div>
      </PageTransition>
    );
  }

  // Admin: 4 tabs
  return (
    <PageTransition>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="mt-1 text-muted-foreground">
            Database, policy, user, and profile management
          </p>
        </div>

        {!config.apiUrl && (
          <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
            <strong>Backend not connected.</strong> Set <strong>NEXT_PUBLIC_API_URL</strong> in{" "}
            <strong>.env.local</strong> (e.g.{" "}
            <code className="rounded bg-muted px-1">http://localhost:8000</code>) and restart.
          </div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <Tabs defaultValue={defaultTab} className="space-y-6">
            <TabsList className="grid w-full grid-cols-4 max-w-2xl">
              <TabsTrigger value="database" className="gap-2">
                <Database className="h-4 w-4" />
                Database
              </TabsTrigger>
              <TabsTrigger value="policy" className="gap-2">
                <FileText className="h-4 w-4" />
                Policy
              </TabsTrigger>
              <TabsTrigger value="users" className="gap-2">
                <Users className="h-4 w-4" />
                Users
              </TabsTrigger>
              <TabsTrigger value="profile" className="gap-2">
                <User className="h-4 w-4" />
                Profile
              </TabsTrigger>
            </TabsList>

            {/* Database Tab */}
            <TabsContent value="database" className="space-y-6">
              <Card className="bg-card/80 backdrop-blur border-border/80">
                <CardHeader>
                  <h3 className="font-semibold">Company database connection</h3>
                  <p className="text-sm text-muted-foreground">
                    Connect the database to scan for compliance violations. After connecting, go to Dashboard and run a comparison.
                  </p>
                </CardHeader>
                <CardContent className="space-y-4">
                  {!config.apiUrl ? (
                    <p className="text-sm text-muted-foreground">Set NEXT_PUBLIC_API_URL to use database connection.</p>
                  ) : (
                    <>
                      {dbConnected && (
                        <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                          Connected to {dbHost || "—"} / {dbName || "—"}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Connect to any database (PostgreSQL or MySQL) via credentials. After a backend restart you must reconnect (password is not saved).
                      </p>
                      <div>
                        <label className="text-sm font-medium">Database type</label>
                        <select
                          value={dbDialect}
                          onChange={(e) => {
                            const d = e.target.value as "postgresql" | "mysql";
                            setDbDialect(d);
                            setDbPort(d === "mysql" ? "3306" : "5432");
                            setDbMessage(null);
                            setDbError(null);
                          }}
                          className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        >
                          <option value="postgresql">PostgreSQL</option>
                          <option value="mysql">MySQL</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-sm font-medium">Host</label>
                        <Input placeholder="localhost or 192.168.1.10" value={dbHost}
                          onChange={(e) => { setDbHost(e.target.value); setDbMessage(null); setDbError(null); }} className="mt-2" />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Port</label>
                        <Input type="number" placeholder={dbDialect === "mysql" ? "3306" : "5432"} value={dbPort}
                          onChange={(e) => { setDbPort(e.target.value); setDbMessage(null); setDbError(null); }} className="mt-2" />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Username</label>
                        <Input placeholder={dbDialect === "mysql" ? "root" : "postgres"} value={dbUsername}
                          onChange={(e) => { setDbUsername(e.target.value); setDbMessage(null); setDbError(null); }} className="mt-2" />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Password</label>
                        <Input type="password" placeholder="••••••••" value={dbPassword}
                          onChange={(e) => { setDbPassword(e.target.value); setDbMessage(null); setDbError(null); }} className="mt-2" />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Database name</label>
                        <Input placeholder="compliance_db" value={dbName}
                          onChange={(e) => { setDbName(e.target.value); setDbMessage(null); setDbError(null); }} className="mt-2" />
                      </div>
                      <Button
                        onClick={async () => {
                          if (!dbHost.trim() || !dbUsername.trim() || !dbName.trim()) return;
                          setDbConnecting(true); setDbMessage(null); setDbError(null);
                          try {
                            await connectDatabase({
                              host: dbHost.trim(),
                              username: dbUsername.trim(),
                              password: dbPassword,
                              db_name: dbName.trim(),
                              port: dbPort ? parseInt(dbPort, 10) : undefined,
                              dialect: dbDialect,
                            });
                            setDbConnected(true);
                            setDbMessage("Connected successfully.");
                          } catch (e) {
                            setDbError(e instanceof Error ? e.message : "Connection failed");
                          } finally {
                            setDbConnecting(false);
                          }
                        }}
                        disabled={dbConnecting || !dbHost.trim() || !dbUsername.trim() || !dbName.trim()}
                      >
                        {dbConnecting ? "Connecting…" : "Connect database"}
                      </Button>
                      {dbMessage && <p className="text-sm text-emerald-600 dark:text-emerald-400">{dbMessage}</p>}
                      {dbError && <p className="text-sm text-destructive">{dbError}</p>}
                    </>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Policy Tab */}
            <TabsContent value="policy" className="space-y-6">
              <Card className="bg-card/80 backdrop-blur border-border/80">
                <CardHeader>
                  <h3 className="font-semibold">Policy Settings</h3>
                  <p className="text-sm text-muted-foreground">
                    Confidence threshold and upload limits (saved to backend)
                  </p>
                </CardHeader>
                <CardContent className="space-y-6">
                  {!config.apiUrl ? (
                    <p className="text-sm text-muted-foreground">Connect the backend to load and save policy settings.</p>
                  ) : settingsLoading ? (
                    <p className="text-sm text-muted-foreground">Loading settings…</p>
                  ) : (
                    <>
                      <div>
                        <label className="text-sm font-medium">Confidence threshold: {confidence}%</label>
                        <input type="range" min="0" max="100" value={confidence}
                          onChange={(e) => setConfidence(Number(e.target.value))} className="mt-2 w-full" />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Max policy upload file size (MB)</label>
                        <Input type="number" min={1} max={500} value={maxFileSizeMb}
                          onChange={(e) => setMaxFileSizeMb(Math.max(1, Math.min(500, Number(e.target.value) || 10)))} className="mt-2" />
                        <p className="mt-1 text-xs text-muted-foreground">Prevents single huge PDFs from exhausting memory.</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium">Max policy uploads per hour</label>
                        <Input type="number" min={0} max={1000} value={maxUploadsPerHour}
                          onChange={(e) => setMaxUploadsPerHour(Math.max(0, Math.min(1000, Number(e.target.value) || 0)))} className="mt-2" />
                        <p className="mt-1 text-xs text-muted-foreground">0 = no limit.</p>
                      </div>
                      <Button
                        disabled={settingsSaving}
                        onClick={async () => {
                          setSettingsSaving(true);
                          try {
                            await updateSettings({ confidence_threshold: confidence, policy_upload_max_file_size_mb: maxFileSizeMb, policy_upload_max_per_hour: maxUploadsPerHour });
                          } finally {
                            setSettingsSaving(false);
                          }
                        }}
                      >
                        {settingsSaving ? "Saving…" : "Save policy settings"}
                      </Button>
                    </>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Users Tab */}
            <TabsContent value="users" className="space-y-6">
              <Card className="bg-card/80 backdrop-blur border-border/80">
                <CardHeader>
                  <h3 className="font-semibold">User Management</h3>
                  <p className="text-sm text-muted-foreground">Add users and assign roles (stored in backend)</p>
                </CardHeader>
                <CardContent className="space-y-6">
                  {config.apiUrl ? (
                    <>
                      <Button
                        onClick={() => { setAddUserOpen(true); setAddUserError(null); setAddUserEmail(""); setAddUserName(""); setAddUserRole("Compliance Officer"); setAddUserDept(""); setAddUserPassword(""); }}
                        className="gap-2"
                      >
                        <UserPlus className="h-4 w-4" />
                        Add user
                      </Button>
                      {usersLoading ? (
                        <p className="text-sm text-muted-foreground">Loading users…</p>
                      ) : usersList.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No users yet. Add a user above.</p>
                      ) : (
                        <div className="overflow-x-auto rounded-lg border border-border/50">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-border/50 bg-muted/30">
                                <th className="px-4 py-3 text-left font-medium">Name</th>
                                <th className="px-4 py-3 text-left font-medium">Email</th>
                                <th className="px-4 py-3 text-left font-medium">Role</th>
                                <th className="px-4 py-3 text-left font-medium">Department</th>
                                <th className="px-4 py-3 text-right font-medium">Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {usersList.map((u) => (
                                <tr key={u.id} className="border-b border-border/30 last:border-0">
                                  <td className="px-4 py-3 font-medium">{u.name}</td>
                                  <td className="px-4 py-3 text-muted-foreground">{u.email}</td>
                                  <td className="px-4 py-3">
                                    <span className="rounded bg-muted px-2 py-0.5 text-xs">{u.role}</span>
                                  </td>
                                  <td className="px-4 py-3 text-muted-foreground">{u.department || "—"}</td>
                                  <td className="px-4 py-3 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                      <Button variant="outline" size="sm"
                                        onClick={() => { setSetPasswordUserId(u.id); setSetPasswordValue(""); setSetPasswordError(null); }}>
                                        Set password
                                      </Button>
                                      <Button variant="outline" size="sm"
                                        className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                        onClick={() => setDeleteConfirmUser({ id: u.id, name: u.name, email: u.email })}>
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">Set NEXT_PUBLIC_API_URL to manage users.</p>
                  )}
                </CardContent>
              </Card>

              {/* Add User Dialog */}
              <Dialog open={addUserOpen} onOpenChange={setAddUserOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add user</DialogTitle>
                    <DialogDescription>
                      Create a new user. Set a password so they can log in. The role determines their access level.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-2">
                    <div>
                      <label className="text-sm font-medium">Email</label>
                      <Input type="email" placeholder="user@company.com" value={addUserEmail}
                        onChange={(e) => setAddUserEmail(e.target.value)} className="mt-2" />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Name</label>
                      <Input placeholder="Full name" value={addUserName}
                        onChange={(e) => setAddUserName(e.target.value)} className="mt-2" />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Role</label>
                      <select
                        value={addUserRole}
                        onChange={(e) => setAddUserRole(e.target.value)}
                        className="mt-2 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                      >
                        <option value="Admin">Admin</option>
                        <option value="Compliance Officer">Compliance Officer</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-sm font-medium">Password</label>
                      <Input type="password" placeholder="Set login password (required to sign in)"
                        value={addUserPassword} onChange={(e) => setAddUserPassword(e.target.value)} className="mt-2" />
                      <p className="mt-1 text-xs text-muted-foreground">They will sign in with this email and password.</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium">Department (optional)</label>
                      <Input placeholder="Operations" value={addUserDept}
                        onChange={(e) => setAddUserDept(e.target.value)} className="mt-2" />
                    </div>
                    {addUserError && <p className="text-sm text-destructive">{addUserError}</p>}
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setAddUserOpen(false)}>Cancel</Button>
                    <Button
                      disabled={!addUserEmail.trim() || addUserSubmitting}
                      onClick={async () => {
                        if (!addUserEmail.trim()) return;
                        setAddUserSubmitting(true); setAddUserError(null);
                        try {
                          await createUser({ email: addUserEmail.trim(), name: addUserName.trim() || addUserEmail.trim().split("@")[0], role: addUserRole, department: addUserDept.trim() || undefined, password: addUserPassword.trim() || undefined });
                          setAddUserOpen(false);
                          loadUsers();
                        } catch (e) {
                          setAddUserError(e instanceof Error ? e.message : "Failed to create user");
                        } finally {
                          setAddUserSubmitting(false);
                        }
                      }}
                    >
                      {addUserSubmitting ? "Creating…" : "Create user"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              {/* Delete User Dialog */}
              <Dialog open={deleteConfirmUser != null} onOpenChange={(open) => { if (!open) { setDeleteConfirmUser(null); setDeleteError(null); } }}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Delete user</DialogTitle>
                    <DialogDescription>
                      Delete <strong>{deleteConfirmUser?.name}</strong> ({deleteConfirmUser?.email})? This cannot be undone.
                    </DialogDescription>
                  </DialogHeader>
                  {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}
                  <DialogFooter>
                    <Button variant="outline" onClick={() => { setDeleteConfirmUser(null); setDeleteError(null); }}>Cancel</Button>
                    <Button variant="destructive" disabled={deleteSubmitting}
                      onClick={async () => {
                        if (deleteConfirmUser == null) return;
                        setDeleteSubmitting(true); setDeleteError(null);
                        try {
                          await deleteUser(deleteConfirmUser.id);
                          setDeleteConfirmUser(null);
                          loadUsers();
                        } catch (e) {
                          setDeleteError(e instanceof Error ? e.message : "Failed to delete user");
                        } finally {
                          setDeleteSubmitting(false);
                        }
                      }}
                    >
                      {deleteSubmitting ? "Deleting…" : "Delete user"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              {/* Set Password Dialog */}
              <Dialog open={setPasswordUserId != null} onOpenChange={(open) => { if (!open) setSetPasswordUserId(null); setSetPasswordError(null); }}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Set password</DialogTitle>
                    <DialogDescription>Set or change this user&apos;s login password.</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-2">
                    <div>
                      <label className="text-sm font-medium">New password</label>
                      <Input type="password" placeholder="Enter new password" value={setPasswordValue}
                        onChange={(e) => setSetPasswordValue(e.target.value)} className="mt-2" />
                    </div>
                    {setPasswordError && <p className="text-sm text-destructive">{setPasswordError}</p>}
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setSetPasswordUserId(null)}>Cancel</Button>
                    <Button
                      disabled={!setPasswordValue.trim() || setPasswordSubmitting}
                      onClick={async () => {
                        if (setPasswordUserId == null || !setPasswordValue.trim()) return;
                        setSetPasswordSubmitting(true); setSetPasswordError(null);
                        try {
                          await setUserPassword(setPasswordUserId, setPasswordValue.trim());
                          setSetPasswordUserId(null); setSetPasswordValue(""); loadUsers();
                        } catch (e) {
                          setSetPasswordError(e instanceof Error ? e.message : "Failed to set password");
                        } finally {
                          setSetPasswordSubmitting(false);
                        }
                      }}
                    >
                      {setPasswordSubmitting ? "Saving…" : "Set password"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </TabsContent>

            {/* Profile Tab */}
            <TabsContent value="profile" className="space-y-6">
              <ProfileCard user={user} />
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </PageTransition>
  );
}
