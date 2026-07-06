# Does sex-conditioning improve DETECTION (not just fit)? Fit central-rel_delta norms on clean-normal
# recordings two ways (sex-conditional m1, sex-pooled m0), then score EVERY recording's abnormality z =
# qnorm(pBCCG(val | age,[sex])). Output z under both so we can compare AUC(normal vs abnormal). If the two
# z's give the same AUC, sex adds nothing to detection and we drop it.
suppressMessages(library(gamlss))
args <- commandArgs(trailingOnly = TRUE); inp <- args[1]; outp <- args[2]
d <- read.csv(inp); d$sex <- factor(d$sex, levels = c("M", "F"))
sm <- "cs(t, df=3)"; ctl <- gamlss.control(trace = FALSE, n.cyc = 200)
zscore <- function(m, nd, y) {
  pa <- predictAll(m, newdata = nd, data = nd0, type = "response")
  qnorm(pmin(pmax(pBCCG(y, mu = pa$mu, sigma = pa$sigma, nu = pa$nu), 1e-6), 1 - 1e-6))
}
out <- list()
for (st in unique(d$stage)) {
  all <- d[d$stage == st & is.finite(d$val) & is.finite(d$t) & !is.na(d$sex), ]
  tr <- all[all$is_train == 1, ]
  if (nrow(tr) < 80 || nrow(all) < 5) next
  nd0 <<- tr
  m1 <- gamlss(as.formula(paste("val ~", sm, "+ sex")), sigma.formula = as.formula(paste("~", sm, "+ sex")),
               nu.formula = ~ 1, family = BCCG, data = tr, control = ctl)
  m0 <- gamlss(as.formula(paste("val ~", sm)), sigma.formula = as.formula(paste("~", sm)),
               nu.formula = ~ 1, family = BCCG, data = tr, control = ctl)
  r <- all[, c("stage", "pos_patho", "pos_genpatho", "pos_focal", "pos_abn", "is_train")]
  r$z_sex <- zscore(m1, all, all$val); r$z_nosex <- zscore(m0, all, all$val)
  out[[st]] <- r
  cat("fit", st, "train=", nrow(tr), "all=", nrow(all), "patho=", sum(all$pos_patho), "abn=", sum(all$pos_abn), "\n")
}
write.csv(do.call(rbind, out), outp, row.names = FALSE)
