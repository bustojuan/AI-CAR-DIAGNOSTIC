export function AssessmentSelector({
  ids,
  selected,
  disabled,
  onSelect,
}: {
  ids: string[];
  selected?: string;
  disabled: boolean;
  onSelect: (id: string) => void;
}) {
  if (ids.length < 2) return null;
  return (
    <label className="assessment-selector">
      Diagnostic assessment
      <select
        aria-label="Diagnostic assessment"
        value={selected || ids.at(-1)}
        disabled={disabled}
        onChange={(event) => onSelect(event.target.value)}
      >
        {ids.map((id, index) => (
          <option value={id} key={id}>
            Assessment {index + 1}
            {index === ids.length - 1 ? " (latest)" : " (historical)"}
          </option>
        ))}
      </select>
    </label>
  );
}
