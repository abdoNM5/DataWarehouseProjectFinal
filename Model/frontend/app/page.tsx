"use client";

import axios from "axios";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  MapPin,
  Sparkles,
} from "lucide-react";

import api from "@/lib/api";
import { StatsResponse } from "@/lib/types";

const compactNumber = new Intl.NumberFormat("en-US");

export default function HomePage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get<StatsResponse>("/stats");
        setStats(response.data);
      } catch (requestError) {
        if (axios.isAxiosError(requestError) && requestError.response?.data?.detail) {
          setError(String(requestError.response.data.detail));
        } else {
          setError("Could not load dashboard stats.");
        }
      } finally {
        setLoading(false);
      }
    };

    void fetchStats();
  }, []);

  const topSkills = stats?.top_skills || [];
  const maxSkillCount = topSkills.reduce(
    (currentMax, skill) => Math.max(currentMax, skill.count),
    1,
  );

  return (
    <div className="page-stack">
      <section className="panel hero-panel">
        <p className="eyebrow">Step E • Home</p>
        <h1>Navigate the Data Job Market with Precision</h1>
        <p className="lede">
          Job Intelligent merges warehouse data with NLP ranking to surface
          offers that truly match your profile.
        </p>

        <div className="actions-row left">
          <Link href="/recommend" className="btn-primary">
            <Sparkles size={16} /> Find Your Match
          </Link>
          <Link href="/offers" className="btn-secondary">
            Browse Offers <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Marketplace Snapshot</h2>
        </div>

        {loading ? (
          <p className="muted">Loading stats...</p>
        ) : error ? (
          <p className="alert error">{error}</p>
        ) : stats ? (
          <div className="stats-grid">
            <article className="stat-card">
              <span className="stat-icon">
                <BriefcaseBusiness size={16} />
              </span>
              <p>Total Offers</p>
              <strong>{compactNumber.format(stats.total_offers)}</strong>
            </article>

            <article className="stat-card">
              <span className="stat-icon">
                <Building2 size={16} />
              </span>
              <p>Total Companies</p>
              <strong>{compactNumber.format(stats.total_companies)}</strong>
            </article>

            <article className="stat-card">
              <span className="stat-icon">
                <MapPin size={16} />
              </span>
              <p>Total Cities</p>
              <strong>{compactNumber.format(stats.total_cities)}</strong>
            </article>
          </div>
        ) : (
          <p className="muted">No stats available.</p>
        )}
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Top Skills Demand</h2>
        </div>

        {topSkills.length === 0 ? (
          <p className="muted">No skills data available yet.</p>
        ) : (
          <div className="skill-cloud-list">
            {topSkills.map((skill, index) => {
              const width = Math.round((skill.count / maxSkillCount) * 100);
              return (
                <article className="skill-cloud-item" key={`${skill.name}-${index}`}>
                  <div className="skill-cloud-head">
                    <span>{skill.name}</span>
                    <strong>{skill.count}</strong>
                  </div>
                  <div className="score-bar-track" aria-hidden="true">
                    <span
                      className="score-bar-fill"
                      style={{ width: `${Math.max(6, width)}%` }}
                    />
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
