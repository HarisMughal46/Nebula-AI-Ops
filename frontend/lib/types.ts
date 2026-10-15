export interface Proc { pid: number; name: string; cpu: number; mem_mb: number }
export interface Alert { ts: number; metric: string; value: number; level: "warning" | "critical"; message: string }
export interface Metrics {
  ts: number; cpu: number; cores: number[]; ram: number; ram_used_gb: number; ram_total_gb: number;
  disk: number; net_up: number; net_down: number; processes?: Proc[]; alerts: Alert[];
}
export interface SystemInfo {
  hostname: string; os: string; os_version: string; cpu_model: string; physical_cores: number | null;
  logical_cores: number; ram_total_gb: number; boot_time: number; uptime_s: number;
}
export interface Settings { cpu_threshold: number; ram_threshold: number; disk_threshold: number }
export interface Insights { source: string; health_score: number; insights: string[] }
export interface ChatMsg { role: "user" | "ai"; text: string; source?: string }
export const API = process.env.NEXT_PUBLIC_API ?? "http://127.0.0.1:8010";
export const fmtRate = (b: number) =>
  b > 1048576 ? `${(b / 1048576).toFixed(1)} MB/s` : `${(b / 1024).toFixed(1)} KB/s`;
export const fmtUptime = (s: number) => {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return `${d ? `${d}d ` : ""}${h}h ${m}m`;
};
