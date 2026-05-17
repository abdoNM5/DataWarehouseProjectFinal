"use client";

import axios from "axios";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ExternalLink, MoveLeft } from "lucide-react";

import api from "@/lib/api";
import { OfferDetail, OfferDetailSkill } from "@/lib/types";

function salaryLine(offer: OfferDetail) {
  if (offer.salary_min === null && offer.salary_max === null) return "Salary not specified";
  if (offer.salary_min !== null && offer.salary_max !== null) {
    return `${offer.salary_min} - ${offer.salary_max} ${offer.currency || ""}`.trim();
  }
  if (offer.salary_min !== null) return `From ${offer.salary_min} ${offer.currency || ""}`.trim();
  return `Up to ${offer.salary_max} ${offer.currency || ""}`.trim();
}

export default function OfferDetailPage() {
  const params = useParams();
  const rawId = params.id;
  const offerId = Array.isArray(rawId) ? rawId[0] : rawId;

  const [offer, setOffer] = useState<OfferDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!offerId) return;

    const fetchOffer = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.get<OfferDetail>(`/offers/${offerId}`);
        setOffer(response.data);
      } catch (requestError) {
        if (axios.isAxiosError(requestError) && requestError.response?.status === 404) {
          setError("Offer not found.");
        } else {
          setError("Could not load offer details.");
        }
      } finally {
        setLoading(false);
      }
    };

    void fetchOffer();
  }, [offerId]);

  const groupedSkills = useMemo(() => {
    const groups: Record<string, OfferDetailSkill[]> = {};

    if (!offer) return groups;

    for (const skill of offer.skills || []) {
      const key = skill.category || "Other";
      if (!groups[key]) groups[key] = [];
      groups[key].push(skill);
    }

    return groups;
  }, [offer]);

  if (loading) {
    return (
      <div className="page-stack">
        <section className="panel">
          <p className="muted">Loading offer details...</p>
        </section>
      </div>
    );
  }

  if (error || !offer) {
    return (
      <div className="page-stack">
        <section className="panel">
          <p className="alert error">{error || "Offer not found."}</p>
          <Link href="/offers" className="inline-link">
            <MoveLeft size={14} /> Back to offers
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <section className="panel hero-panel compact">
        <Link href="/offers" className="inline-link">
          <MoveLeft size={14} /> Back to offers
        </Link>
        <p className="eyebrow">Offer #{offer.offer_id}</p>
        <h1>{offer.title}</h1>
        <p className="lede">
          {offer.company} {offer.city ? `— ${offer.city}` : ""}
        </p>
        <div className="chip-wrap compact">
          <span className="chip neutral">{offer.job_family}</span>
          <span className="chip neutral">{salaryLine(offer)}</span>
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Description</h2>
        </div>
        <div className="description-box">
          {offer.description?.trim() ? offer.description : "No description provided."}
        </div>

        {offer.url && (
          <div className="actions-row left">
            <a href={offer.url} target="_blank" rel="noreferrer" className="btn-secondary">
              <ExternalLink size={14} /> Open Original Posting
            </a>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Extracted Skills</h2>
        </div>

        {Object.keys(groupedSkills).length === 0 ? (
          <p className="muted">No extracted skills available for this offer.</p>
        ) : (
          <div className="skills-groups-grid">
            {Object.entries(groupedSkills).map(([category, skills]) => (
              <article key={category} className="skill-group-card">
                <h3>{category}</h3>
                <div className="chip-wrap compact">
                  {skills.map((skill) => (
                    <span className="chip" key={`${category}-${skill.name}`}>
                      {skill.name}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
