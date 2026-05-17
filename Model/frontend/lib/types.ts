export type SkillItem = {
  name: string;
  category: string;
};

export type TopSkill = {
  name: string;
  count: number;
};

export type StatsResponse = {
  total_offers: number;
  total_companies: number;
  total_cities: number;
  top_skills: TopSkill[];
};

export type OfferSummary = {
  offer_id: number;
  title: string;
  job_family: string;
  company: string;
  city: string | null;
  salary_min: number | null;
  salary_max: number | null;
};

export type OfferDetailSkill = {
  name: string;
  category: string;
  confidence: number;
};

export type OfferDetail = {
  offer_id: number;
  title: string;
  job_family: string;
  company: string;
  city: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  description: string | null;
  url: string | null;
  skills: OfferDetailSkill[];
};

export type RecommendRequest = {
  description: string;
  skills: string[];
  top_k: number;
};

export type OfferResult = {
  offer_id: number;
  title: string;
  job_family: string;
  company: string;
  city: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  match_score: number;
  semantic_score: number;
  skill_score: number;
  matched_skills: string[];
  missing_skills: string[];
};

export type RecommendResponse = {
  recommendations: OfferResult[];
  total_offers_searched: number;
  processing_time_ms: number;
};
