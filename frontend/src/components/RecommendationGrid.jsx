import RecommendationCard from './RecommendationCard'

export default function RecommendationGrid({ recommendations }) {
  if (!recommendations?.length) return null

  return (
    <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {recommendations.map((rec, i) => (
        <RecommendationCard key={`${rec.url}-${i}`} rec={rec} index={i} />
      ))}
    </div>
  )
}
