export type UserProfile = {
  role: "investor" | "issuer" | "admin";
  is_issuer: boolean;
  is_investor: boolean;
  subscription_status: string;
  current_plan: string | null;
  has_active_subscription: boolean;
};

export type CurrentUser = {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  profile: UserProfile;
};

export type ZsaConfig = {
  configured: boolean;
  ready: boolean;
  missing: string[];
  warnings: string[];
  backend: string;
  method: string;
  network?: string;
  safe_display: Record<string, unknown>;
};

export type TokenizationSummary = {
  status: string;
  status_display: string;
  operation_id: string | null;
  txid: string | null;
  asset_id: string | null;
  error: string | null;
  tokenized_at: string | null;
};

export type PropertyRecord = {
  id: number;
  title: string;
  description: string;
  address: string;
  latitude: string | null;
  longitude: string | null;
  size_sqm: number;
  bedrooms: number | null;
  bathrooms: number | null;
  estimated_value: string | null;
  total_shares: number;
  status: string;
  status_display: string;
  tokenization: TokenizationSummary;
  document_count: number;
  created_at: string | null;
  updated_at: string | null;
  ownership: {
    is_owner: boolean;
    can_edit: boolean;
    can_upload_documents: boolean;
    can_tokenize: boolean;
  };
  documents?: DocumentRecord[];
  tokenization_operations?: TokenizationOperation[];
};

export type DocumentRecord = {
  id: number;
  document_type: string;
  document_hash: string;
  processing_status: string;
  safe_extracted_metadata: Record<string, string | boolean | number>;
  uploaded_at: string | null;
  processed_at: string | null;
};

export type TokenizationOperation = {
  id: number;
  property: {
    id: number;
    title: string;
  };
  status: string;
  backend: string;
  method: string;
  asset_symbol: string;
  total_shares: number;
  issuer_zaddr_masked: string | null;
  operation_id: string | null;
  txid: string | null;
  asset_id: string | null;
  safe_metadata: Record<string, unknown>;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
  broadcast_at: string | null;
  confirmed_at: string | null;
  failed_at: string | null;
  last_status_refreshed_at: string | null;
  can_refresh: boolean;
  can_view_raw_response: boolean;
  raw_response?: Record<string, unknown>;
};

export type IssuerDashboard = {
  metrics: {
    property_count: number;
    tokenized_count: number;
    total_estimated_value: string | null;
    zsa_issued_count: number;
  };
  zsa_config: ZsaConfig;
  properties: PropertyRecord[];
};

export type InvestorDashboard = {
  metrics: {
    investment_count: number;
    available_property_count: number;
    total_portfolio_value: string | null;
  };
  holdings: Array<{
    id: number;
    property: PropertyRecord;
    shares_owned: number;
    ownership_percent: string;
    estimated_position_value: string | null;
    purchase_date: string | null;
    purchase_tx_hash: string | null;
  }>;
};
