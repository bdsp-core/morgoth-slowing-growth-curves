# GAMLSS/LMS normative fit, SEX POOLED (one curve per sleep stage). Sex was shown to add nothing to
# abnormality detection (dAUC <=0.002 on the real TAR/DAR detector; see scripts/74), so we pool sexes and
# estimate each stage's age trajectory from all the data. Per STAGE: BCCG (Box-Cox Cole-Green) with
# mu ~ smooth(age), sigma ~ smooth(age), nu ~ 1; centiles via qBCCG.
# method: auto (pb, ML penalty) | smooth (low-df cubic spline) | fp (fractional polynomials).
suppressMessages(library(gamlss))
args <- commandArgs(trailingOnly = TRUE)
inp <- args[1]; outp <- args[2]; method <- ifelse(length(args) >= 3, args[3], "smooth")
d <- read.csv(inp)
cents <- c(3, 10, 25, 50, 75, 90, 97)
tmin <- min(d$t[is.finite(d$t)]); d$tp <- d$t - tmin + 1
# method: keyword (auto/smooth/fp) OR a number = cubic-spline df for mu (more df -> follows the sharp
# infant elbow; the log-age axis keeps the data-dense adult range stable so extra df doesn't wiggle there).
numdf <- suppressWarnings(as.numeric(method))
if (!is.na(numdf)) {
  agesmooth <- sprintf("cs(t, df=%g)", numdf)
  sigdf <- max(2, min(numdf - 2, 4))                # sigma stays smoother than mu to avoid wavy bands
  sigsmooth <- sprintf("cs(t, df=%g)", sigdf)
} else {
  agesmooth <- switch(method, auto = "pb(t)", smooth = "cs(t, df=5)", fp = "fp(tp, 2)")
  sigsmooth <- switch(method, auto = "pb(t)", smooth = "cs(t, df=4)", fp = "fp(tp, 2)")
}
# Skewness (nu) is modeled as a smooth function of age: young ages are far more right-skewed than old,
# and a constant nu biases the median (mu) high there. BCT adds a kurtosis (tau) term for heavier tails.
# Fall back to the simpler BCCG/constant-nu fit if the richer model fails to converge for a stage.
nusmooth <- "cs(t, df=3)"
res <- list()
for (st in unique(d$stage)) {
  sub <- d[d$stage == st & is.finite(d$val) & is.finite(d$t), ]
  if (nrow(sub) < 80) next
  fmu <- as.formula(paste("val ~", agesmooth))
  fsig <- as.formula(paste("~", sigsmooth))
  fnu  <- as.formula(paste("~", nusmooth))
  ctl <- gamlss.control(trace = FALSE, n.cyc = 200)
  # richer model first: BCT (skew+kurtosis) with age-varying skewness; fall back to BCCG/constant-nu
  m <- tryCatch(gamlss(fmu, sigma.formula = fsig, nu.formula = fnu, family = BCT, data = sub, control = ctl),
                error = function(e) NULL)
  fam <- "BCT"
  if (is.null(m)) {
    m <- tryCatch(gamlss(fmu, sigma.formula = fsig, nu.formula = ~ 1, family = BCCG, data = sub, control = ctl),
                  error = function(e) NULL); fam <- "BCCG"
  }
  if (is.null(m)) { cat("FAIL", st, "\n"); next }
  tg <- seq(min(sub$t), max(sub$t), length.out = 160)
  nd <- data.frame(t = tg, tp = tg - tmin + 1)
  pa <- tryCatch(predictAll(m, newdata = nd, data = sub, type = "response"), error = function(e) NULL)
  if (is.null(pa)) { cat("PREDFAIL", st, "\n"); next }
  qfun <- if (fam == "BCT") function(p) qBCT(p, mu = pa$mu, sigma = pa$sigma, nu = pa$nu, tau = pa$tau)
          else function(p) qBCCG(p, mu = pa$mu, sigma = pa$sigma, nu = pa$nu)
  row <- data.frame(t = tg)
  for (p in cents) row[[paste0("p", p)]] <- qfun(p / 100)
  row$group <- st
  res[[st]] <- row
  cat("ok", st, method, fam, "n=", nrow(sub), "edf(mu)=", round(m$mu.df, 1), "\n")
}
write.csv(do.call(rbind, res), outp, row.names = FALSE)
