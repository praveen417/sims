import axios from "axios";

export const api = axios.create({ baseURL: "/api", paramsSerializer: { indexes: null } });
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (f) => { onUnauthorized = f; };

api.interceptors.request.use((cfg) => {
  const t = sessionStorage.getItem("sims_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !String(err.config?.url).includes("/auth/login")) onUnauthorized();
    return Promise.reject(err);
  }
);

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (Array.isArray(d)) return d.map((x) => `${(x.loc || []).slice(1).join(".")}: ${x.msg}`).join("; ");
  return d || e?.message || "Request failed";
}

export async function download(url, params) {
  const r = await api.get(url, { params, responseType: "blob" });
  const m = /filename="?([^";]+)"?/.exec(r.headers["content-disposition"] || "");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(r.data);
  a.download = m ? m[1] : "download";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}
