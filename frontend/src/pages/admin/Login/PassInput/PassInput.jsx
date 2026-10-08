import { useRef, useState } from 'react';
import './PassInput.css';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLock, faEye, faEyeSlash } from '@fortawesome/free-solid-svg-icons';

function PassInput({ placeholder, value, onChange }) {
  const [isVisible, setIsVisible] = useState(false);
  const inputRef = useRef(null);

  function toggleVisibility() {
    setIsVisible((prev) => !prev);
    setTimeout(() => {
      const input = inputRef.current;
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    }, 0);
  }

  return (
    <div className="PassInputRoot">
      <span className="PassIcon">
        <FontAwesomeIcon icon={faLock} />
      </span>
      <input
        ref={inputRef}
        className="PassInputContainer"
        type={isVisible ? 'text' : 'password'}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <button
        type="button"
        className="eyeIcon"
        onClick={toggleVisibility}
        aria-label={isVisible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
      >
        <FontAwesomeIcon icon={isVisible ? faEyeSlash : faEye} />
      </button>
    </div>
  );
}

export default PassInput;