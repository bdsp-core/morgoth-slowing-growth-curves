# GAMLSS/BCT z-scores — SAP §6.1/§6.3.
# Fits BCT (Box-Cox-t: mu=median, sigma=scale, nu=SKEW, tau=KURTOSIS), each a smooth function of age,
# per sleep stage, on the NORMAL reference only; then returns proper BCT z-scores for a set of
# observations to score. This replaces the normal-theory z = (x-mean)/sd of the Gaussian-kernel path,
# which misstates centiles on right-skewed features (worst in children — see gamlss_fit.R notes).
#
# Usage: Rscript gamlss_zscore.R <fit.csv> <score.csv> <out.csv>
#   fit.csv  : stage, t (= log10(age + 1/12)), val   -- the clean_normal reference to FIT on
#   score.csv: id, stage, t, val                     -- observations to SCORE (may include abnormals)
#   out.csv  : id, stage, z                          -- BCT z-scores
suppressMessages(library(gamlss))
args <- commandArgs(trailingOnly = TRUE)
fit_f <- args[1]; score_f <- args[2]; out_f <- args[3]

fit <- read.csv(fit_f); sco <- read.csv(score_f)
fit <- fit[is.finite(fit$t) & is.finite(fit$val) & fit$val > 0, ]
res <- list()

for (st in unique(sco$stage)) {
  f <- fit[fit$stage == st, ]
  s <- sco[sco$stage == st, ]
  if (nrow(s) == 0) next
  # need enough reference points to fit a 4-parameter distribution smoothly in age
  if (nrow(f) < 100) { res[[st]] <- data.frame(id = s$id, stage = st, z = NA_real_); next }

  m <- try(gamlss(val ~ cs(t, df = 5),
                  sigma.fo = ~ cs(t, df = 4),
                  nu.fo    = ~ cs(t, df = 3),   # skew smooth in age (the whole point)
                  tau.fo   = ~ 1,
                  family = BCT, data = f, trace = FALSE), silent = TRUE)
  if (inherits(m, "try-error")) {
    # fall back to BCCG (no kurtosis term) if BCT will not converge for this stage
    m <- try(gamlss(val ~ cs(t, df = 5), sigma.fo = ~ cs(t, df = 4), nu.fo = ~ cs(t, df = 3),
                    family = BCCG, data = f, trace = FALSE), silent = TRUE)
  }
  if (inherits(m, "try-error")) { res[[st]] <- data.frame(id = s$id, stage = st, z = NA_real_); next }

  # BCT z-scores for the observations (skew/kurtosis-corrected, NOT (x-mean)/sd)
  z <- try(centiles.pred(m, xname = "t", xvalues = s$t, yval = s$val, type = "z-scores"),
           silent = TRUE)
  if (inherits(z, "try-error")) z <- rep(NA_real_, nrow(s))
  res[[st]] <- data.frame(id = s$id, stage = st, z = as.numeric(z))
}

out <- if (length(res)) do.call(rbind, res) else data.frame(id = character(), stage = character(), z = numeric())
write.csv(out, out_f, row.names = FALSE)
