export function Tag({ color, children }) {
  return <span className="tag" style={{ '--c': color }}>{children}</span>
}

export function Tags({ question, topics, areas, max, style }) {
  const codes = question.c || []
  const shown = codes.slice(0, max)
  return (
    <div className="tags" style={style}>
      {shown.map((code) => topics[code] && (
        <Tag key={code} color={areas[topics[code][1]]}>{topics[code][0]}</Tag>
      ))}
      {codes.length > max && <span className="tag more">+{codes.length - max}</span>}
    </div>
  )
}
