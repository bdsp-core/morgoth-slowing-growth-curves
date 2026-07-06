# Does conditioning on SEX change our ability to detect abnormalities?
# For each stage fit two BCCG/LMS models on central rel_delta:
#   m1: mu ~ s(age)+sex, sigma ~ s(age)+sex   (sex-conditional norms)
#   m0: mu ~ s(age),     sigma ~ s(age)        (sex-pooled, no sex)
# The z-score we'd flag on = normalized quantile residual (deterministic for BCCG). If sex matters for
# detection, z must move: we report |dz|=|z_sex - z_nosex| and, critically, how many recordings cross the
# |z|=1.96 abnormal threshold DIFFERENTLY under the two models (flips). BIC says if sex earns its params.
suppressMessages(library(gamlss))
args <- commandArgs(trailingOnly = TRUE); inp <- args[1]; outp <- args[2]
d <- read.csv(inp); d$sex <- factor(d$sex, levels = c("M", "F"))
sm <- "cs(t, df=3)"; ctl <- gamlss.control(trace = FALSE, n.cyc = 200)
rows <- list(); summ <- list()
for (st in unique(d$stage)) {
  sub <- d[d$stage == st & is.finite(d$val) & is.finite(d$t) & !is.na(d$sex), ]
  if (nrow(sub) < 80) next
  m1 <- gamlss(as.formula(paste("val ~", sm, "+ sex")), sigma.formula = as.formula(paste("~", sm, "+ sex")),
               nu.formula = ~ 1, family = BCCG, data = sub, control = ctl)
  m0 <- gamlss(as.formula(paste("val ~", sm)), sigma.formula = as.formula(paste("~", sm)),
               nu.formula = ~ 1, family = BCCG, data = sub, control = ctl)
  z1 <- residuals(m1); z0 <- residuals(m0); dz <- abs(z1 - z0)
  sub$z_sex <- z1; sub$z_nosex <- z0
  rows[[st]] <- sub[, c("stage", "sex", "t", "z_sex", "z_nosex")]
  flip <- sum((abs(z1) > 1.96) != (abs(z0) > 1.96))
  summ[[st]] <- data.frame(stage = st, n = nrow(sub),
    bic_sex = round(GAIC(m1, k = log(nrow(sub))), 0), bic_nosex = round(GAIC(m0, k = log(nrow(sub))), 0),
    dbic = round(GAIC(m0, k = log(nrow(sub))) - GAIC(m1, k = log(nrow(sub))), 1),
    dz_med = round(median(dz), 3), dz_p95 = round(quantile(dz, .95), 3), dz_max = round(max(dz), 3),
    flips = flip, flip_pct = round(100 * flip / nrow(sub), 2))
}
S <- do.call(rbind, summ); print(S, row.names = FALSE)
write.csv(do.call(rbind, rows), outp, row.names = FALSE)
# dbic = BIC(no-sex) - BIC(sex); lower BIC is better, so dbic>0 => the SEX model fits better (worth its
# params), dbic<0 => drop sex. flips = recordings crossing |z|=1.96 differently (detection instability).
cat("\ndbic>0 => BIC prefers the SEX model; dbic<0 => drop sex.\n")
cat("dz = |z_withsex - z_nosex| in SD units; flips = recordings that cross |z|=1.96 differently.\n")
