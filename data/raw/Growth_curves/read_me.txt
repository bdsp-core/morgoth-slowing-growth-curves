Each row in table "res" represents one 15sec segment that has 4 columns:
- column 1: morgoth sleep stage	0: W
				1: N1
				2: N2
				3: N3
				4: R
				5: Other
			    
- column 2: start point of the segment

- column 3: end point of the segment

- column 4: feature array (18x31)
	    18 bipolar channels:'Fp1-F7'
				'F7-T3'
				'T3-T5'
				'T5-O1'
				'Fp2-F8'
				'F8-T4'
				'T4-T6'
				'T6-O2'
				'Fp1-F3'
				'F3-C3'
				'C3-P3'
				'P3-O1'
				'Fp2-F4'
				'F4-C4'
				'C4-P4'
				'P4-O2'
				'Fz-Cz'
				'Cz-Pz'
				
	     31 power features:	'delta-power'
				'theta-power'
				'alpha-power'
				'beta-power'
				'gamma-power'
				'total-power'
				'delta/total'
				'theta/total'
				'alpha/total'
				'beta/total'
				'gamma/total'
				'delta/theta'
				'delta/alpha'
				'delta/beta'
				'delta/gamma'
				'theta/delta'
				'theta/alpha'
				'theta/beta'
				'theta/gamma'
				'alpha/delta'
				'alpha/theta'
				'alpha/beta'
				'alpha/gamma'
				'beta/delta'
				'beta/theta'
				'beta/alpha'
				'beta/gamma'
				'gamma/delta'
				'gamma/theta'
				'gamma/alpha'
				'gamma/beta'
					    
