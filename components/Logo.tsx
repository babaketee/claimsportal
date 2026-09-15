export function Logo({
  variant = "color",
  size = 40,
  showTagline = false,
}: {
  variant?: "color" | "white";
  size?: number;
  showTagline?: boolean;
}) {
  const wordColor = variant === "white" ? "#ffffff" : "#0f4f48";
  const checkColor = variant === "white" ? "#ffffff" : "#eb2229";
  const assureColor = variant === "white" ? "rgba(255,255,255,0.88)" : "#eb2229";

  return (
    <div className="inline-flex flex-col leading-none">
      <div className="inline-flex items-baseline">
        <span className="relative inline-block leading-none">
          <span style={{ fontSize: size, color: wordColor }} className="block font-black leading-none">
            D
          </span>
          <span
            style={{
              fontSize: size * 0.6,
              color: checkColor,
              top: size * 0.06,
              left: size * 0.03,
            }}
            className="absolute font-black leading-none"
          >
            &#10003;
          </span>
        </span>
        <span
          style={{ fontSize: size, color: wordColor, marginLeft: -1 }}
          className="font-black leading-none"
        >
          efinite
        </span>
      </div>
      <div
        style={{
          fontSize: size * 0.27,
          color: assureColor,
          letterSpacing: "0.38em",
          marginTop: size * 0.07,
          paddingLeft: 2,
        }}
        className="font-bold"
      >
        ASSURANCE
      </div>
      {showTagline && (
        <div className="mt-2 text-xs italic text-brand-red/90">You Are Definitely Covered</div>
      )}
    </div>
  );
}
