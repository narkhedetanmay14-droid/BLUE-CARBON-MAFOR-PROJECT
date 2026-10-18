import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api, token } from "./services/api";
import RegionMap from "./components/RegionMap";

type User = { id: string; username: string; display_name: string; role: "user" | "admin" };
type Project = Record<string, any>;

const normalLinks = [
  ["/", "Dashboard"],
  ["/register-project", "Register Project"],
  ["/projects", "My Projects"],
  ["/project-analysis", "Project Analysis"],
  ["/marketplace", "Marketplace"],
  ["/profile", "Profile"],
];

const adminLinks = [
  ["/", "Admin Dashboard"],
  ["/admin/verification", "Project Verification"],
  ["/admin/analysis", "Project Analysis"],
  ["/admin/audit-logs", "Audit Logs"],
  ["/admin/users", "User Profiles"],
  ["/profile", "Profile"],
];

function Shell({ user, children, onLogout }: { user: User; children: React.ReactNode; onLogout: () => void }) {
  const links = user.role === "admin" ? adminLinks : normalLinks;
  return (
    <div className="shell">
      <aside>
        <div className="brand">🌿 Blue Carbon</div>
        <nav>
          {links.map(([to, label]) => (
            <Link key={to} to={to}>
              {label}
            </Link>
          ))}
        </nav>
        <button onClick={onLogout}>Log out</button>
      </aside>
      <main>
        <header>
          <div>
            <small>BLUE CARBON REGISTRATION AND MONITORING</small>
            <h1>{user.role === "admin" ? "Administrator workspace" : "Environmental project workspace"}</h1>
          </div>
          <span className="role">{user.role}</span>
        </header>
        {children}
      </main>
    </div>
  );
}

function Login({ onLogin }: { onLogin: (user: User, accessToken: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [register, setRegister] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      if (register) {
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({ username, password, display_name: displayName }),
        });
        setRegister(false);
        setMessage("Account created. Sign in with it now.");
      } else {
        const result = await api("/auth/login", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        });
        onLogin(result.user, result.access_token);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to continue");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="logo">🌱</div>
        <h1>Blue Carbon</h1>
        <p>Registration and monitoring portal</p>
        {register && (
          <label>
            Display name
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
          </label>
        )}
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} />
        </label>
        <label>
          Password
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={register ? 10 : 1}
            type="password"
          />
        </label>
        {message && <p className="notice">{message}</p>}
        <button className="primary" disabled={busy}>
          {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
        </button>
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setRegister(!register);
            setMessage("");
          }}
        >
          {register ? "Already registered? Sign in" : "Create a normal user account"}
        </button>
        <small>Administrator accounts can only be created locally with scripts/create_admin.py.</small>
      </form>
    </div>
  );
}

function Dashboard({ user }: { user: User }) {
  const [data, setData] = useState<any>();
  const [error, setError] = useState("");
  useEffect(() => {
    api(user.role === "admin" ? "/dashboard/admin" : "/dashboard/user")
      .then(setData)
      .catch((e) => setError(e.message));
  }, [user]);

  if (error) return <p className="notice">{error}</p>;
  if (!data) return <p>Loading dashboard…</p>;

  const cards =
    user.role === "admin"
      ? [
          ["Users", data.users],
          ["Projects", data.projects],
          ["Pending reviews", data.pending_reviews],
          ["Mapped area (ha)", data.total_area_hectares],
        ]
      : [
          ["My projects", data.total_projects],
          ["Pending", data.pending_projects],
          ["Approved", data.approved_projects],
          ["Mapped area (ha)", data.total_area_hectares],
          ["Available credits (tCO2e)", data.credits ?? "Not recorded"],
        ];

  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">MONITOR • VERIFY • RESTORE</span>
          <h2>
            {user.role === "admin"
              ? "Review verified coastal-project records."
              : "Protect coastal ecosystems with traceable project records."}
          </h2>
          <p>
            {user.role === "admin"
              ? "Review submissions and use the approved-project analysis without accessing normal-user workflows."
              : "Register mapped regions, track verification, and retain separate analysis evidence."}
          </p>
          {user.role !== "admin" && (
            <Link className="primary inline" to="/register-project">
              ＋ Register a project
            </Link>
          )}
        </div>
        <div className="hero-art">
          🌊<span>🌿</span>
        </div>
      </section>
      <div className="metrics">
        {cards.map(([label, value]) => (
          <article className="metric" key={String(label)}>
            <small>{label}</small>
            <strong>{value ?? "N/A"}</strong>
          </article>
        ))}
      </div>
      <section className="panel">
        <h2>{user.role === "admin" ? "Verification and analysis" : "Analysis status"}</h2>
        <p>
          Machine-learning analysis and administrative verification are tracked independently. Carbon values remain
          unavailable until compatible georeferenced raster imagery and a calibrated biomass model are configured.
        </p>
      </section>
    </>
  );
}

function Projects() {
  const [items, setItems] = useState<Project[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/projects")
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <section className="panel">
      <h2>My Projects</h2>
      {error && <p className="notice">{error}</p>}
      {!error && items.length === 0 ? (
        <p>No projects registered yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Location</th>
                <th>Area (ha)</th>
                <th>Verification</th>
                <th>ML analysis</th>
              </tr>
            </thead>
            <tbody>
              {items.map((project) => (
                <tr key={project.id}>
                  <td>
                    <Link to={`/projects/${project.id}`}>{project.name}</Link>
                    <small>{project.id}</small>
                  </td>
                  <td>{[project.locality, project.state, project.country].filter(Boolean).join(", ")}</td>
                  <td>{project.area_hectares}</td>
                  <td>
                    <span className="status">{project.verification_status}</span>
                  </td>
                  <td>{project.ml_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ProjectForm({ project }: { project?: Project }) {
  const nav = useNavigate();
  const draftKey = "bc_project_registration_draft";

  // Restore draft from sessionStorage if not editing an existing project
  const [name, setName] = useState(() => project?.name || (!project ? sessionStorage.getItem(`${draftKey}_name`) || "" : ""));
  const [description, setDescription] = useState(() => project?.description || (!project ? sessionStorage.getItem(`${draftKey}_desc`) || "" : ""));
  const [ecosystem, setEcosystem] = useState(() => project?.ecosystem_type || (!project ? sessionStorage.getItem(`${draftKey}_eco`) || "mangrove" : "mangrove"));
  const [country, setCountry] = useState(() => project?.country || (!project ? sessionStorage.getItem(`${draftKey}_cntry`) || "India" : "India"));
  const [state, setState] = useState(() => project?.state || (!project ? sessionStorage.getItem(`${draftKey}_state`) || "" : ""));
  const [locality, setLocality] = useState(() => project?.locality || (!project ? sessionStorage.getItem(`${draftKey}_loc`) || "" : ""));

  const [geometry, setGeometry] = useState<any>(() => {
    if (project?.geojson) return project.geojson;
    if (!project) {
      const saved = sessionStorage.getItem(`${draftKey}_geom`);
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          return null;
        }
      }
    }
    return null;
  });

  const [referenceId, setReferenceId] = useState<string | null>(() => {
    if (project?.reference_region_id) return project.reference_region_id;
    if (!project) return sessionStorage.getItem(`${draftKey}_ref_id`);
    return null;
  });

  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  // Persist draft to sessionStorage when editing a new submission
  useEffect(() => {
    if (project) return;
    sessionStorage.setItem(`${draftKey}_name`, name);
    sessionStorage.setItem(`${draftKey}_desc`, description);
    sessionStorage.setItem(`${draftKey}_eco`, ecosystem);
    sessionStorage.setItem(`${draftKey}_cntry`, country);
    sessionStorage.setItem(`${draftKey}_state`, state);
    sessionStorage.setItem(`${draftKey}_loc`, locality);
    if (geometry) sessionStorage.setItem(`${draftKey}_geom`, JSON.stringify(geometry));
    if (referenceId) sessionStorage.setItem(`${draftKey}_ref_id`, referenceId);
  }, [name, description, ecosystem, country, state, locality, geometry, referenceId, project]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!geometry) {
      setMessage("Select a CSV reference region or draw a valid polygon before submitting.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const body = {
        name,
        description,
        ecosystem_type: ecosystem,
        country,
        state,
        locality,
        geojson: geometry,
        reference_region_id: referenceId,
      };
      const saved = await api(project ? `/projects/${project.id}/resubmit` : "/projects", {
        method: "POST",
        body: JSON.stringify(body),
      });

      // Clear draft on successful submission
      if (!project) {
        sessionStorage.removeItem(`${draftKey}_name`);
        sessionStorage.removeItem(`${draftKey}_desc`);
        sessionStorage.removeItem(`${draftKey}_eco`);
        sessionStorage.removeItem(`${draftKey}_cntry`);
        sessionStorage.removeItem(`${draftKey}_state`);
        sessionStorage.removeItem(`${draftKey}_loc`);
        sessionStorage.removeItem(`${draftKey}_geom`);
        sessionStorage.removeItem(`${draftKey}_ref_id`);
      }

      nav(`/projects/${saved.id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save project");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>{project ? `Correct and resubmit: ${project.name}` : "Register a blue-carbon project"}</h2>
      <p>
        CSV-backed district polygons are yellow. The active selected region is red, faithfully restored across navigation
        and page reloads.
      </p>
      <RegionMap
        initialGeometry={geometry}
        initialReferenceRegionId={referenceId}
        onChange={(value, selection) => {
          setGeometry(value);
          setReferenceId(selection.referenceRegionId);
          if (selection.referenceRegion) {
            if (selection.referenceRegion.district && !locality) setLocality(selection.referenceRegion.district);
            if (!state) setState("West Bengal");
          }
        }}
      />
      <form className="project-form" onSubmit={submit}>
        <label>
          Project name
          <input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
        </label>
        <label>
          Ecosystem
          <select value={ecosystem} onChange={(e) => setEcosystem(e.target.value)}>
            <option value="mangrove">Mangrove</option>
            <option value="seagrass">Seagrass</option>
            <option value="salt_marsh">Salt marsh</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>
          Country
          <input value={country} onChange={(e) => setCountry(e.target.value)} required />
        </label>
        <label>
          State / province
          <input value={state} onChange={(e) => setState(e.target.value)} />
        </label>
        <label>
          District / locality
          <input value={locality} onChange={(e) => setLocality(e.target.value)} />
        </label>
        <label className="wide">
          Description
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Saving…" : project ? "Resubmit for review" : "Save project for review"}
        </button>
      </form>
      {message && <p className="notice">{message}</p>}
    </section>
  );
}

function RegisterProject() {
  return <ProjectForm />;
}

function EditProject() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project>();
  const [message, setMessage] = useState("");
  useEffect(() => {
    api(`/projects/${projectId}`)
      .then(setProject)
      .catch((e) => setMessage(e.message));
  }, [projectId]);

  if (message) return <p className="notice">{message}</p>;
  return project ? <ProjectForm project={project} /> : <p>Loading project…</p>;
}

function ProjectDetails() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project>();
  const [assessments, setAssessments] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    if (!projectId) return;
    Promise.all([api(`/projects/${projectId}`), api(`/projects/${projectId}/assessments`)])
      .then(([p, a]) => {
        setProject(p);
        setAssessments(a);
      })
      .catch((e) => setMessage(e.message));
  }, [projectId]);

  async function analyze() {
    if (!project) return;
    setBusy(true);
    try {
      const assessment = await api(`/projects/${project.id}/analyze`, { method: "POST" });
      setAssessments((current) => [...current, assessment]);
      setProject({ ...project, ml_status: assessment.status });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to run analysis");
    } finally {
      setBusy(false);
    }
  }

  if (message) return <p className="notice">{message}</p>;
  if (!project) return <p>Loading project…</p>;
  const canResubmit = ["rejected", "corrections_requested"].includes(project.verification_status);

  return (
    <section className="panel">
      <div className="title-row">
        <div>
          <h2>{project.name}</h2>
          <p className="muted">{project.id}</p>
        </div>
        <span className="status">{project.verification_status}</span>
      </div>
      <div className="detail-grid">
        <p>
          <strong>Location</strong>
          <br />
          {[project.locality, project.state, project.country].filter(Boolean).join(", ") || "Not supplied"}
        </p>
        <p>
          <strong>Ecosystem</strong>
          <br />
          {project.ecosystem_type}
        </p>
        <p>
          <strong>Mapped area</strong>
          <br />
          {project.area_hectares} ha
        </p>
        <p>
          <strong>ML analysis</strong>
          <br />
          <span style={{ color: project.ml_status === "insufficient_data" ? "#b45309" : "inherit" }}>
            {project.ml_status}
          </span>
        </p>
      </div>
      {project.reference_region && (
        <section className="reference-card">
          <strong>CSV reference data</strong>
          <p>
            {project.reference_region.district} ·{" "}
            {project.reference_region.total_mangrove_cover_km2 || "Not available"} km² mangrove cover ·{" "}
            {project.reference_region.assessment_year || "Year not available"}
          </p>
        </section>
      )}
      <h3>Saved project boundary</h3>
      <RegionMap initialGeometry={project.geojson} initialReferenceRegionId={project.reference_region_id} readOnly />
      {canResubmit && (
        <button className="primary" onClick={() => nav(`/projects/${project.id}/edit`)}>
          Correct and resubmit
        </button>
      )}
      <section className="analysis-section">
        <h3>Honest ML analysis evidence</h3>
        {assessments.length ? (
          assessments.map((item) => (
            <article className="reference-card" key={item.id}>
              <strong>Status: {item.status}</strong>
              <p>{item.methodology}</p>
              {item.limitations && (
                <ul style={{ margin: "8px 0 0", paddingLeft: "20px", color: "#6b7280" }}>
                  {item.limitations.map((lim: string, idx: number) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              )}
            </article>
          ))
        ) : (
          <p>
            No ML analysis has been run for this project. Its administrative verification status remains{" "}
            <strong>{project.verification_status}</strong>.
          </p>
        )}
        <button onClick={analyze} disabled={busy}>
          {busy ? "Running analysis…" : "Run / check ML analysis"}
        </button>
      </section>
    </section>
  );
}

function UserAnalysis() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api("/projects"), api("/analysis/reference-summary")])
      .then(([projs, sum]) => {
        setProjects(projs);
        setSummary(sum);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <section className="panel">
      <h2>Project & Reference Data Analysis</h2>
      {error && <p className="notice">{error}</p>}
      {summary && (
        <section className="reference-card" style={{ marginBottom: "20px" }}>
          <strong>Reference Dataset Analysis (Official Surveys vs Demonstration Data)</strong>
          <p>{summary.scientific_integrity_notice}</p>
          <div className="detail-grid" style={{ marginTop: "12px" }}>
            <p>
              <strong>Verified observations</strong>
              <br />
              {summary.verified_observations?.count} district records ({summary.verified_observations?.sum_district_cover_km2} km² total cover)
            </p>
            <p>
              <strong>Synthetic demo records</strong>
              <br />
              {summary.synthetic_demonstration?.count} sample plots (clearly demarcated)
            </p>
            <p>
              <strong>Predictive Model Status</strong>
              <br />
              {summary.ml_readiness?.predictive_model_deployable ? "Deployable" : "Unavailable (Insufficient Data)"}
            </p>
          </div>
        </section>
      )}
      <h3>My Registered Projects</h3>
      {!error && !projects.length && <p>No saved projects have analysis records yet.</p>}
      {projects.map((project) => (
        <article className="review-item" key={project.id}>
          <div>
            <h3>
              <Link to={`/projects/${project.id}`}>{project.name}</Link>
            </h3>
            <p>
              ML analysis: <strong>{project.ml_status}</strong> · Administrative verification:{" "}
              <strong>{project.verification_status}</strong>
            </p>
            <small>Open project for saved geometry and transparent methodology limits.</small>
          </div>
        </article>
      ))}
    </section>
  );
}

function AdminVerification() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  const refresh = () =>
    api("/admin/projects")
      .then(setProjects)
      .catch((e) => setMessage(e.message));
  useEffect(() => {
    refresh();
  }, []);

  async function decide(id: string, action: "approve" | "reject" | "request-corrections") {
    const reason = reasons[id]?.trim() || "";
    if (action !== "approve" && reason.length < 3) {
      setMessage("A structured rejection or correction reason of at least three characters is required.");
      return;
    }
    try {
      await api(`/admin/projects/${id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      setMessage("Verification decision recorded and audited.");
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to record decision");
    }
  }

  const queue = projects.filter((project) =>
    ["pending", "corrections_requested"].includes(project.verification_status)
  );

  return (
    <section className="panel">
      <h2>Project Verification</h2>
      <p>Only the administrator can make these persisted decisions. Rejection and correction requests require a reason.</p>
      {message && <p className="notice">{message}</p>}
      {!queue.length && <p>No submissions require review.</p>}
      {queue.map((project) => (
        <article className="review-item" key={project.id}>
          <div>
            <h3>{project.name}</h3>
            <p>
              {[project.locality, project.state, project.country].filter(Boolean).join(", ")} · {project.area_hectares} ha · ML:{" "}
              {project.ml_status}
            </p>
            <details>
              <summary>Inspect saved region and project details</summary>
              <p>
                Owner ID: {project.owner_id}
                <br />
                Reference region: {project.reference_region?.district || "Custom region"}
              </p>
              <RegionMap
                initialGeometry={project.geojson}
                initialReferenceRegionId={project.reference_region_id}
                readOnly
              />
            </details>
          </div>
          <div className="decision-box">
            <textarea
              aria-label={`Reason for ${project.name}`}
              placeholder="Required for reject/corrections"
              value={reasons[project.id] || ""}
              onChange={(e) => setReasons({ ...reasons, [project.id]: e.target.value })}
            />
            <div className="actions">
              <button onClick={() => decide(project.id, "approve")}>Approve</button>
              <button onClick={() => decide(project.id, "request-corrections")}>Request corrections</button>
              <button className="danger" onClick={() => decide(project.id, "reject")}>
                Reject
              </button>
            </div>
          </div>
        </article>
      ))}
    </section>
  );
}

function AdminAnalysis() {
  const [items, setItems] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    Promise.all([api("/admin/analysis"), api("/admin/analysis/summary")])
      .then(([rows, sum]) => {
        setItems(rows);
        setSummary(sum);
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, []);

  return (
    <section className="panel">
      <h2>Approved Project Analysis</h2>
      <p>
        Strictly contains only authoritative approved projects. Credit usage is calculated solely from explicit persisted
        ledger events.
      </p>
      {busy ? (
        <p>Loading analysis…</p>
      ) : error ? (
        <p className="notice">{error}</p>
      ) : (
        <>
          {summary && (
            <div className="metrics" style={{ marginBottom: "20px" }}>
              <article className="metric">
                <small>Approved projects</small>
                <strong>{summary.total_approved_projects}</strong>
              </article>
              <article className="metric">
                <small>Total approved area (ha)</small>
                <strong>{summary.total_approved_area_hectares}</strong>
              </article>
              <article className="metric">
                <small>Allocated credits (tCO2e)</small>
                <strong>{summary.total_carbon_credits_allocated}</strong>
              </article>
              <article className="metric">
                <small>Credits used (tCO2e)</small>
                <strong>{summary.total_carbon_credits_used}</strong>
              </article>
            </div>
          )}

          {summary?.regional_holdings && Object.keys(summary.regional_holdings).length > 0 && (
            <section style={{ marginBottom: "24px" }}>
              <h3>Regional Holdings Summary</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Region / District</th>
                      <th>Approved projects</th>
                      <th>Total area (ha)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(summary.regional_holdings).map(([reg, val]: [string, any]) => (
                      <tr key={reg}>
                        <td>
                          <strong>{reg}</strong>
                        </td>
                        <td>{val.project_count}</td>
                        <td>{val.total_area_hectares} ha</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <h3>Approved Project Details</h3>
          {!items.length ? (
            <p>No approved projects are available.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Owner</th>
                    <th>Region</th>
                    <th>Area (ha)</th>
                    <th>Verification</th>
                    <th>User Credit Balance</th>
                    <th>Carbon Credits Used</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.project_id}>
                      <td>
                        <strong>{item.project_name}</strong>
                        <small>{item.project_id}</small>
                      </td>
                      <td>{item.owner.display_name || item.owner.username || "Not available"}</td>
                      <td>{item.regional_holding}</td>
                      <td>{item.area_hectares}</td>
                      <td>
                        <span className="status">{item.verification_status}</span>
                      </td>
                      <td>
                        {item.user_balance ? (
                          <span>
                            {item.user_balance.remaining} / {item.user_balance.allocated} {item.user_balance.units}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        {item.carbon_credit_usage_status === "available"
                          ? `${item.carbon_credit_usage} tCO2e`
                          : "Not available"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function AuditLogs() {
  const [items, setItems] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    setBusy(true);
    const query = statusFilter !== "all" ? `?status=${encodeURIComponent(statusFilter)}` : "";
    api(`/admin/audit-logs${query}`)
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, [statusFilter]);

  return (
    <section className="panel">
      <div className="title-row">
        <div>
          <h2>Audit & Review History</h2>
          <p>Traceable history of all administrative verification decisions and system compliance events.</p>
        </div>
        <div>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
            Status filter:
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">All statuses</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="corrections_requested">Corrections requested</option>
              <option value="pending_review">Pending review / Resubmitted</option>
            </select>
          </label>
        </div>
      </div>

      {busy ? (
        <p>Loading audit history…</p>
      ) : error ? (
        <p className="notice">{error}</p>
      ) : !items.length ? (
        <p>No audit events match the selected criteria.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>Project</th>
                <th>Decision / Status</th>
                <th>Reviewer</th>
                <th>Timestamp</th>
                <th>Reason / Details</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={item.id || index}>
                  <td>
                    <strong>{item.event}</strong>
                  </td>
                  <td>
                    {item.project_name ? <span>{item.project_name}</span> : <small className="muted">{item.project_id || "System"}</small>}
                  </td>
                  <td>
                    {item.status ? (
                      <span className="status">{item.status}</span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>{item.reviewer_name || "System"}</td>
                  <td>
                    <small>{item.review_timestamp ? new Date(item.review_timestamp).toLocaleString() : "Not recorded"}</small>
                  </td>
                  <td>
                    <small>{item.reason || item.message || "—"}</small>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function AdminUserProfiles() {
  const [users, setUsers] = useState<any[]>([]);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [profileData, setProfileData] = useState<any>(null);
  const [error, setError] = useState("");
  const [loadingProfile, setLoadingProfile] = useState(false);

  useEffect(() => {
    api("/admin/users")
      .then(setUsers)
      .catch((e) => setError(e.message));
  }, []);

  async function viewUser(u: any) {
    setSelectedUser(u);
    setLoadingProfile(true);
    setProfileData(null);
    try {
      const data = await api(`/admin/users/${u.id}/profile`);
      setProfileData(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingProfile(false);
    }
  }

  return (
    <section className="panel">
      <h2>Registered User Profiles & Holdings</h2>
      <p>Administrative view of user accounts, approved project counts, and verified approval timestamps.</p>
      {error && <p className="notice">{error}</p>}
      <div style={{ display: "grid", gridTemplateColumns: selectedUser ? "1fr 1fr" : "1fr", gap: "20px" }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Approved projects</th>
                <th>Total projects</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ background: selectedUser?.id === u.id ? "#f0fdf4" : "inherit" }}>
                  <td>
                    <strong>{u.display_name || u.username}</strong>
                    <small>@{u.username}</small>
                  </td>
                  <td>
                    <span className="role">{u.role}</span>
                  </td>
                  <td>
                    <strong>{u.approved_projects_count ?? 0}</strong>
                  </td>
                  <td>{u.total_projects_count ?? 0}</td>
                  <td>
                    <button className="primary" style={{ padding: "6px 10px", fontSize: "12px" }} onClick={() => viewUser(u)}>
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedUser && (
          <div className="panel" style={{ background: "#f8fbf9", border: "1px solid #d1fae5" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>{selectedUser.display_name} (@{selectedUser.username})</h3>
              <button onClick={() => setSelectedUser(null)} style={{ padding: "4px 8px" }}>
                ✕ Close
              </button>
            </div>
            {loadingProfile ? (
              <p>Loading profile details…</p>
            ) : profileData ? (
              <>
                <p>
                  <strong>Approved projects count:</strong> {profileData.approved_project_count}
                  <br />
                  <strong>Total approved mapped area:</strong> {profileData.total_approved_area_hectares} ha
                </p>
                <h4>Approved projects</h4>
                {!profileData.approved_projects.length ? (
                  <p className="muted">This user has no approved projects.</p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Project</th>
                          <th>Area (ha)</th>
                          <th>Approval Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {profileData.approved_projects.map((p: any) => (
                          <tr key={p.project_id}>
                            <td>
                              <strong>{p.name}</strong>
                              <small>{[p.location?.locality, p.location?.state].filter(Boolean).join(", ")}</small>
                            </td>
                            <td>{p.area_hectares}</td>
                            <td>
                              <small>
                                {p.approval_timestamp ? new Date(p.approval_timestamp).toLocaleDateString() : "Not recorded"}
                              </small>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            ) : null}
          </div>
        )}
      </div>
    </section>
  );
}

function Marketplace() {
  const [projects, setProjects] = useState<any[]>([]);
  const [listings, setListings] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    setBusy(true);
    Promise.all([api("/marketplace/projects"), api("/marketplace/listings")])
      .then(([projs, lists]) => {
        setProjects(projs);
        setListings(lists);
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, []);

  async function handleBuy(listingId: string) {
    setNotice("");
    try {
      await api(`/marketplace/listings/${listingId}/purchase`, {
        method: "POST",
        body: JSON.stringify({ quantity: 1 }),
      });
      setNotice("Purchase confirmed.");
    } catch (e: any) {
      setNotice(`Purchase transfer: ${e.message}`);
    }
  }

  return (
    <section className="panel">
      <h2>Blue Carbon Marketplace</h2>
      <p>
        Browse project-supported carbon credit availability. In accordance with authoritative standards, credits are only
        represented as available when administrative verification is approved and certified.
      </p>

      {notice && <p className="notice">{notice}</p>}
      {error && <p className="notice">{error}</p>}

      {busy ? (
        <p>Loading marketplace listings…</p>
      ) : (
        <>
          <h3>Active Credit Batches & Listings</h3>
          {!listings.length ? (
            <p>
              No active credit listings currently available for immediate trading. Verified issuance requires external
              methodology compliance.
            </p>
          ) : (
            <div className="table-wrap" style={{ marginBottom: "28px" }}>
              <table>
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Region</th>
                    <th>Quantity (tCO2e)</th>
                    <th>Price / credit</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {listings.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.project_name}</strong>
                        <small>{item.credit_id}</small>
                      </td>
                      <td>{item.region || "Sundarbans"}</td>
                      <td>{item.remaining_quantity || item.quantity}</td>
                      <td>${item.price_per_credit}</td>
                      <td>
                        <span className="status">{item.status}</span>
                      </td>
                      <td>
                        <button className="primary" style={{ padding: "6px 12px" }} onClick={() => handleBuy(item.id)}>
                          Purchase
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>Supported Projects & Availability</h3>
          {!projects.length ? (
            <p>No projects registered in the system.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Region / Location</th>
                    <th>Ecosystem</th>
                    <th>Area (ha)</th>
                    <th>Approval Status</th>
                    <th>Available Credits</th>
                    <th>Availability</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((p) => (
                    <tr key={p.project_id}>
                      <td>
                        <strong>{p.name}</strong>
                        <small>{p.project_id}</small>
                      </td>
                      <td>{p.region || [p.locality, p.state].filter(Boolean).join(", ")}</td>
                      <td>{p.ecosystem_type}</td>
                      <td>{p.area_hectares} ha</td>
                      <td>
                        <span className="status">{p.verification_status}</span>
                      </td>
                      <td>
                        <strong>{p.available_credits} tCO2e</strong>
                      </td>
                      <td>
                        {p.availability_status === "available" ? (
                          <span style={{ color: "#059669", fontWeight: 600 }}>● Available</span>
                        ) : (
                          <small className="muted">
                            {p.verification_status === "approved"
                              ? "No credits issued yet"
                              : "Requires project approval"}
                          </small>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Profile({ user }: { user: User }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    api("/auth/profile")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, [user]);

  if (busy) {
    return (
      <section className="panel">
        <h2>Profile</h2>
        <p>Loading authenticated user profile and ledger balance…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel">
        <h2>Profile</h2>
        <p className="notice">{error}</p>
      </section>
    );
  }

  const alloc = data?.allocations || [];
  const balance = data?.balance ?? "Not recorded";
  const hasRecords = data?.has_authoritative_records;

  return (
    <section className="panel">
      <h2>User Profile & Carbon Balance</h2>
      <div className="detail-grid" style={{ marginBottom: "20px" }}>
        <p>
          <strong>Display name</strong>
          <br />
          {user.display_name}
        </p>
        <p>
          <strong>Username</strong>
          <br />
          @{user.username}
        </p>
        <p>
          <strong>Account Role</strong>
          <br />
          <span className="role">{user.role}</span>
        </p>
        <p>
          <strong>User ID</strong>
          <br />
          <small className="muted">{user.id}</small>
        </p>
      </div>

      <div className="metrics" style={{ marginBottom: "20px" }}>
        <article className="metric">
          <small>Total Allocated</small>
          <strong>{data?.total_allocated ?? 0} tCO2e</strong>
        </article>
        <article className="metric">
          <small>Used / Deducted</small>
          <strong>{data?.total_deductions ?? 0} tCO2e</strong>
        </article>
        <article className="metric">
          <small>Net Remaining Balance</small>
          <strong>{hasRecords ? `${data?.remaining_balance ?? 0} tCO2e` : "Not recorded"}</strong>
        </article>
      </div>

      <h3>Project-Wise Carbon Allocations</h3>
      {alloc.length === 0 ? (
        <p className="muted">
          No project carbon allocations found in authoritative records. Available balances remain unallocated until
          credits are certified and issued.
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Status</th>
                <th>Allocated (tCO2e)</th>
                <th>Used / Reserved (tCO2e)</th>
                <th>Remaining (tCO2e)</th>
              </tr>
            </thead>
            <tbody>
              {alloc.map((a: any) => (
                <tr key={a.project_id || a.id}>
                  <td>
                    <strong>{a.project_name || a.project_id}</strong>
                    <small>{a.project_id}</small>
                  </td>
                  <td>
                    <span className="status">{a.verification_status}</span>
                  </td>
                  <td>{a.allocated}</td>
                  <td>{a.consumed}</td>
                  <td>
                    <strong>{a.remaining}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3>Authoritative Ledger Status</h3>
      <p>
        Ledger state: <strong>{data?.ledger_status || "not_recorded"}</strong>.
        {!hasRecords && (
          <span className="muted" style={{ display: "block", marginTop: "4px" }}>
            Authoritative ledger records have not yet been issued for this account. Values are derived strictly from persistent
            storage without fabrication.
          </span>
        )}
      </p>
    </section>
  );
}

function NormalRoute({ user, children }: { user: User; children: React.ReactNode }) {
  return user.role === "user" ? <>{children}</> : <Navigate to="/" replace />;
}

function AdminRoute({ user, children }: { user: User; children: React.ReactNode }) {
  return user.role === "admin" ? <>{children}</> : <Navigate to="/" replace />;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    if (token()) {
      api("/auth/me")
        .then(setUser)
        .catch(() => localStorage.removeItem("bc_token"));
    }
  }, []);

  function login(nextUser: User, accessToken: string) {
    localStorage.setItem("bc_token", accessToken);
    setUser(nextUser);
    nav("/");
  }

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // Session might already be expired
    }
    localStorage.removeItem("bc_token");
    setUser(null);
    nav("/");
  }

  if (!user) return <Login onLogin={login} />;

  return (
    <Shell user={user} onLogout={logout}>
      <Routes>
        <Route path="/" element={<Dashboard user={user} />} />
        <Route path="/profile" element={<Profile user={user} />} />
        <Route
          path="/register-project"
          element={
            <NormalRoute user={user}>
              <RegisterProject />
            </NormalRoute>
          }
        />
        <Route
          path="/projects"
          element={
            <NormalRoute user={user}>
              <Projects />
            </NormalRoute>
          }
        />
        <Route
          path="/projects/:projectId"
          element={
            <NormalRoute user={user}>
              <ProjectDetails />
            </NormalRoute>
          }
        />
        <Route
          path="/projects/:projectId/edit"
          element={
            <NormalRoute user={user}>
              <EditProject />
            </NormalRoute>
          }
        />
        <Route
          path="/project-analysis"
          element={
            <NormalRoute user={user}>
              <UserAnalysis />
            </NormalRoute>
          }
        />
        <Route
          path="/marketplace"
          element={
            <NormalRoute user={user}>
              <Marketplace />
            </NormalRoute>
          }
        />
        <Route
          path="/admin/verification"
          element={
            <AdminRoute user={user}>
              <AdminVerification />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/analysis"
          element={
            <AdminRoute user={user}>
              <AdminAnalysis />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/audit-logs"
          element={
            <AdminRoute user={user}>
              <AuditLogs />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <AdminRoute user={user}>
              <AdminUserProfiles />
            </AdminRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
