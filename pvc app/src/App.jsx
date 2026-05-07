import { useState, useRef } from "react";
import "./App.css";

const API_BASE = "http://localhost:5000";

function App() {
  const [data, setData] = useState(null);

  const [radius, setRadius] = useState(20);

  const [border, setBorder] = useState(2);

  const [cardType, setCardType] = useState("normal");

  const [loading, setLoading] = useState(false);

  // FILE INPUT REF
  const fileRef = useRef(null);

  // =========================
  // UPLOAD
  // =========================
  const handleUpload = async (e) => {
    const file = e.target.files[0];

    if (!file) return;

    setLoading(true);

    const fd = new FormData();

    fd.append("file", file);

    fd.append("type", cardType);

    try {
      const res = await fetch(`${API_BASE}/init`, {
        method: "POST",
        body: fd,
      });

      const json = await res.json();

      setData(json);
    } catch (err) {
      console.log(err);

      alert("Upload Failed");
    }

    setLoading(false);
  };

  // =========================
  // DOWNLOAD
  // =========================
  const handleDownload = async () => {
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          session_id: data.session_id,
          radius,
          border,
          type: cardType,
        }),
      });

      const blob = await res.blob();

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");

      link.href = url;

      link.download = "id_card_final.pdf";

      document.body.appendChild(link);

      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.log(err);

      alert("Download Failed");
    }

    setLoading(false);
  };

  // =========================
  // CARD SIZE
  // =========================
  const getCardSize = () => {
    switch (cardType) {
      case "aadhaar_pvc":
        return {
          width: "350px",
          height: "220px",
        };

      case "voter":
        return {
          width: "380px",
          height: "240px",
        };

      default:
        return {
          width: "360px",
          height: "225px",
        };
    }
  };

  const size = getCardSize();

  const cardStyle = {
    width: size.width,

    height: size.height,

    borderRadius: `${radius}px`,

    border: `${border}px solid #111`,
  };

  return (
    <div className="app">
      <div className="main-card">
        {/* =========================
            TOP
        ========================= */}

        <div className="top">
          <div>
            <h1>ID Card Generator</h1>

            <p>Create PVC, Aadhaar & Voter ID printable cards</p>
          </div>

          {/* <div className="badge">React + Flask</div> */}
        </div>

        {/* =========================
            CONTROLS
        ========================= */}

        <div className="controls">
          <div className="select-box">
            <label>Card Type</label>

            <select
              value={cardType}
              onChange={(e) => {
                setCardType(e.target.value);

                setData(null);

                if (fileRef.current) {
                  fileRef.current.value = "";
                }
              }}
            >
              <option value="normal">Aadhaar</option>

              <option value="aadhaar_pvc">Aadhaar PVC</option>

              <option value="voter">Voter ID</option>
            </select>
          </div>

          {/* =========================
              UPLOAD
          ========================= */}

          <label className="upload-box">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              onChange={handleUpload}
            />

            <div className="upload-inner">
              <div className="upload-icon">📄</div>

              <div className="upload-title">
                {loading ? "Processing..." : "Upload PDF"}
              </div>

              <div className="upload-sub">Select Aadhaar or Voter PDF</div>
            </div>
          </label>
        </div>

        {/* =========================
            PREVIEW
        ========================= */}

        {data && (
          <>
            <div className="preview-wrapper">
              {/* FRONT */}

              <div className="preview-card" style={cardStyle}>
                <img src={`data:image/png;base64,${data.front}`} alt="Front" />
              </div>

              {/* BACK */}

              <div className="preview-card" style={cardStyle}>
                <img src={`data:image/png;base64,${data.back}`} alt="Back" />
              </div>
            </div>

            {/* =========================
                SLIDERS
            ========================= */}

            <div className="slider-area">
              {/* RADIUS */}

              <div className="slider-box">
                <div className="slider-head">
                  <span>Corner Radius</span>

                  <b>{radius}px</b>
                </div>

                <input
                  type="range"
                  min="0"
                  max="80"
                  value={radius}
                  onChange={(e) => setRadius(Number(e.target.value))}
                />
              </div>

              {/* BORDER */}

              <div className="slider-box">
                <div className="slider-head">
                  <span>Border Thickness</span>

                  <b>{border}px</b>
                </div>

                <input
                  type="range"
                  min="0"
                  max="20"
                  value={border}
                  onChange={(e) => setBorder(Number(e.target.value))}
                />
              </div>
            </div>

            {/* =========================
                DOWNLOAD BUTTON
            ========================= */}

            <button
              className="download-btn"
              onClick={handleDownload}
              disabled={loading}
            >
              {loading ? "Generating PDF..." : "Download PDF"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
