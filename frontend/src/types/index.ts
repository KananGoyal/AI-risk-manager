export type DefenseAction = 'allow' | 'flag_for_review' | 'hold_for_verification' | 'auto_decline';
export type RiskBand = 'low' | 'medium' | 'high' | 'very_high';

export interface CohortContext {
  merchant: string;
  merchant_category: string;
  historical_mean_amount: number;
  historical_std_amount?: number;
  amount_ratio_vs_baseline: number;
  baseline_zscore: number;
  historical_fraud_rate?: number;
}

export interface ScoredTransaction {
  id?: number;
  transaction_id: string;
  timestamp: string;
  merchant: string;
  merchant_category: string;
  amount: number;
  card_num?: string;
  device_id?: string;
  risk_score: number; // 0.0 to 1.0
  risk_band: RiskBand;
  action: DefenseAction;
  cohort_context: CohortContext;
  top_features?: Record<string, number>;
  explanation?: string;
  threshold_used?: number;
  estimated_fp_cost?: number;
  estimated_fraud_caught?: number;
  created_at?: string;
}

export interface ThresholdCurvePoint {
  threshold: number;
  precision: number;
  recall: number;
  f1_score: number;
  tp_count?: number;
  fp_count?: number;
  fn_count?: number;
  estimated_fp_cost: number;
  estimated_fraud_caught: number;
  estimated_fn_cost?: number;
  net_loss?: number;
}

export interface ThresholdAnalysisResponse {
  optimal_threshold: number;
  recommended_bands: {
    low: { max: number; action: string };
    medium: { min: number; max: number; action: string };
    high: { min: number; max: number; action: string };
    very_high: { min: number; max: number; action: string };
  };
  threshold_curve: ThresholdCurvePoint[];
}

export interface StreamResponse {
  count: number;
  transactions: ScoredTransaction[];
}
