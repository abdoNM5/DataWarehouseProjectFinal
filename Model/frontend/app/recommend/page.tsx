"use client";

import axios from "axios";
import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Search, Sparkles, X } from "lucide-react";

import api from "@/lib/api";
import { OfferResult, RecommendResponse, SkillItem } from "@/lib/types";

const TOP_K = 10;

function getScoreColor(score: number) {
  if (score >= 0.8) return "var(--ok)";
  if (score >= 0.6) return "var(--warn)";
  return "var(--bad)";
}

function toPercent(score: number) {
  return Math.min(100, Math.max(4, Math.round(score * 100)));
}

export default function RecommendPage() {
  const [allSkills, setAllSkills] = useState<SkillItem[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [description, setDescription] = useState("");

  const [results, setResults] = useState<OfferResult[]>([]);
  const [totalOffersSearched, setTotalOffersSearched] = useState<number | null>(null);
  const [processingTimeMs, setProcessingTimeMs] = useState<number | null>(null);

  const [loadingSkills, setLoadingSkills] = useState(true);
  const [loadingResults, setLoadingResults] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSkills = async () => {
      try {
        const response = await api.get<SkillItem[]>("/skills");
        setAllSkills(response.data);
      } catch {
        setError("Could not load skills list. Please retry.");
      } finally {
        setLoadingSkills(false);
      }
    };

    void fetchSkills();
  }, []);

  const suggestions = useMemo(() => {
    const keyword = searchTerm.trim().toLowerCase();
    if (!keyword) return [];

    return allSkills
      .filter(
        (skill) =>
          skill.name.toLowerCase().includes(keyword) &&
          !selectedSkills.includes(skill.name),
      )
      .slice(0, 8);
  }, [allSkills, searchTerm, selectedSkills]);

  const addSkill = (skillName: string) => {
    if (selectedSkills.includes(skillName)) return;
    setSelectedSkills((prev) => [...prev, skillName]);
    setSearchTerm("");
  };

  const removeSkill = (skillName: string) => {
    setSelectedSkills((prev) => prev.filter((item) => item !== skillName));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    const cleanDescription = description.trim();
    if (cleanDescription.length < 10) {
      setError("Please describe your ideal role with at least 10 characters.");
      return;
    }

    setLoadingResults(true);

    try {
      const response = await api.post<RecommendResponse>("/recommend", {
        description: cleanDescription,
        skills: selectedSkills,
        top_k: TOP_K,
      });

      setResults(response.data.recommendations);
      setTotalOffersSearched(response.data.total_offers_searched);
      setProcessingTimeMs(response.data.processing_time_ms);
    } catch (requestError) {
      if (axios.isAxiosError(requestError) && requestError.response?.data?.detail) {
        setError(String(requestError.response.data.detail));
      } else {
        setError("Recommendation request failed. Please try again.");
      }
    } finally {
      setLoadingResults(false);
    }
  };

  return (
    <div className="page-stack">
      <section className="panel hero-panel">
        <p className="eyebrow">Step E • Star Feature</p>
        <h1>Find Your Best Job Match</h1>
        <p className="lede">
          Blend your skills and your intent. This page combines semantic NLP and
          skill overlap from your recommendation engine.
        </p>
      </section>

      <section className="panel">
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="field-group">
            <label htmlFor="skill-search" className="field-label">
              Select Skills
            </label>

            <div className="search-wrap">
              <Search size={16} />
              <input
                id="skill-search"
                placeholder={
                  loadingSkills ? "Loading skills..." : "Type to search skills"
                }
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                disabled={loadingSkills}
              />
            </div>

            {suggestions.length > 0 && (
              <ul className="suggestion-list" role="listbox">
                {suggestions.map((skill) => (
                  <li key={skill.name}>
                    <button
                      type="button"
                      className="suggestion-item"
                      onClick={() => addSkill(skill.name)}
                    >
                      <span>{skill.name}</span>
                      <small>{skill.category}</small>
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div className="chip-wrap" aria-live="polite">
              {selectedSkills.length === 0 && (
                <span className="chip-placeholder">No skills selected yet.</span>
              )}

              {selectedSkills.map((skill) => (
                <button
                  key={skill}
                  type="button"
                  className="chip removable"
                  onClick={() => removeSkill(skill)}
                >
                  <span>{skill}</span>
                  <X size={14} />
                </button>
              ))}
            </div>
          </div>

          <div className="field-group">
            <label htmlFor="profile-description" className="field-label">
              Candidate Description
            </label>
            <textarea
              id="profile-description"
              placeholder="Describe your ideal job role, experience, and interests..."
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              minLength={10}
              rows={6}
            />
            <div className="meta-line">
              <span>{description.length} characters</span>
              <span>Top results: {TOP_K}</span>
            </div>
          </div>

          <div className="actions-row">
            <button type="submit" className="btn-primary" disabled={loadingResults}>
              <Sparkles size={16} />
              {loadingResults ? "Matching offers..." : "Get Recommendations"}
            </button>
          </div>

          {error && (
            <p className="alert error" role="alert">
              <AlertTriangle size={16} />
              <span>{error}</span>
            </p>
          )}
        </form>
      </section>

      {results.length > 0 && (
        <section className="panel">
          <div className="section-head">
            <h2>Recommendation Results</h2>
            {totalOffersSearched !== null && processingTimeMs !== null && (
              <p className="meta-line">
                Found {results.length} matches out of {totalOffersSearched} offers in {" "}
                {processingTimeMs}ms
              </p>
            )}
          </div>

          <div className="results-grid">
            {results.map((result, index) => {
              const percent = toPercent(result.match_score);

              return (
                <article key={result.offer_id} className="result-card">
                  <div className="result-top">
                    <p className="rank">#{index + 1}</p>
                    <p className="score">Score {percent}%</p>
                  </div>

                  <h3>{result.title}</h3>
                  <p className="result-meta">
                    {result.company} {result.city ? `— ${result.city}` : ""}
                  </p>

                  <div className="score-bar-track" aria-hidden="true">
                    <span
                      className="score-bar-fill"
                      style={{
                        width: `${percent}%`,
                        backgroundColor: getScoreColor(result.match_score),
                      }}
                    />
                  </div>

                  <div className="skills-split">
                    <div>
                      <p className="skills-label">Matched</p>
                      <div className="chip-wrap compact">
                        {result.matched_skills.length === 0 && (
                          <span className="chip-placeholder">No direct overlap</span>
                        )}
                        {result.matched_skills.map((skill) => (
                          <span className="chip positive" key={`${result.offer_id}-${skill}`}>
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="skills-label">Missing</p>
                      <div className="chip-wrap compact">
                        {result.missing_skills.length === 0 && (
                          <span className="chip-placeholder">No missing skill</span>
                        )}
                        {result.missing_skills.map((skill) => (
                          <span className="chip negative" key={`${result.offer_id}-missing-${skill}`}>
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="result-footer">
                    <span className="metric">Semantic {toPercent(result.semantic_score)}%</span>
                    <span className="metric">Skill {toPercent(result.skill_score)}%</span>
                    <Link href={`/offers/${result.offer_id}`} className="inline-link">
                      View Details <ArrowRight size={14} />
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
