# Batch GAMLSS/BCT normative fit for the descriptor grid (SAP §6.1). Fits ONE BCT (Box-Cox-t) per cell —
# mu=median, sigma=scale, nu=SKEW, tau=KURTOSIS, each smooth in t=log10(age+1/12) — on the clean_normal
# reference, and exports the four parameter curves on a dense t-grid so Python can compute a per-segment
# BCT z-score (validated to match centiles.pred to 3e-4). BCCG fallback (no kurtosis) if BCT will not
# converge; a cell that fails both is simply omitted (Python falls back to a log-age kernel for it).
#
# Usage: Rscript gamlss_norm_grid.R <in.csv> <out.csv> <mu_df>
#   in.csv : cell, t, val         (cell = "stage|region|feature")
#   out.csv: cell, t, mu, sigma, nu, tau, fam
suppressMessages(library(gamlss))
args <- commandArgs(trailingOnly = TRUE)
inp <- args[1]; outp <- args[2]
mu_df <- if (length(args) >= 3) as.numeric(args[3]) else 8
sig_df <- max(2, min(mu_df - 2, 4))
nu_df  <- 3
NG <- 120                                   # grid points per cell

d <- read.csv(inp)
d <- d[is.finite(d$t) & is.finite(d$val) & d$val > 0, ]
res <- list()
ctl <- gamlss.control(trace = FALSE, n.cyc = 200)

for (cell in unique(d$cell)) {
  sub <- d[d$cell == cell, ]
  if (nrow(sub) < 200) next
  # cap for speed; BCT on >30k points buys nothing
  if (nrow(sub) > 30000) sub <- sub[sample(nrow(sub), 30000), ]
  fmu  <- as.formula(sprintf("val ~ cs(t, df=%g)", mu_df))
  fsig <- as.formula(sprintf("~ cs(t, df=%g)", sig_df))
  fnu  <- as.formula(sprintf("~ cs(t, df=%g)", nu_df))
  # penalized-spline variants (data chooses smoothness) are robust where a fixed-df cs() will not converge
  fmu_pb <- val ~ pb(t); fsig_pb <- ~ pb(t); fnu_pb <- ~ pb(t)
  tryfit <- function(fm, fs, fn, fam) tryCatch(
    gamlss(fm, sigma.formula = fs, nu.formula = fn, family = fam, data = sub, control = ctl),
    error = function(e) NULL)
  # BCT cs(df) -> BCT pb() -> BCCG cs(df) -> BCCG pb(); fall through to Python log-age kernel if all fail
  m <- tryfit(fmu, fsig, fnu, BCT);                 fam <- "BCT"
  if (is.null(m)) { m <- tryfit(fmu_pb, fsig_pb, fnu_pb, BCT);  fam <- "BCT" }
  if (is.null(m)) { m <- tryfit(fmu, fsig, fnu, BCCG);          fam <- "BCCG" }
  if (is.null(m)) { m <- tryfit(fmu_pb, fsig_pb, fnu_pb, BCCG); fam <- "BCCG" }
  if (is.null(m)) { cat("FAIL", cell, "\n"); next }
  tg <- seq(min(sub$t), max(sub$t), length.out = NG)
  pa <- tryCatch(predictAll(m, newdata = data.frame(t = tg), data = sub, type = "response"),
                 error = function(e) NULL)
  if (is.null(pa)) { cat("PREDFAIL", cell, "\n"); next }
  tau <- if (fam == "BCT") pa$tau else rep(1e6, length(tg))    # BCCG = BCT with tau->Inf (normal kernel)
  res[[cell]] <- data.frame(cell = cell, t = tg, mu = pa$mu, sigma = pa$sigma,
                            nu = pa$nu, tau = tau, fam = fam)
  cat("ok", cell, fam, "n=", nrow(sub), "edf(mu)=", round(m$mu.df, 1), "\n")
}
write.csv(do.call(rbind, res), outp, row.names = FALSE)
