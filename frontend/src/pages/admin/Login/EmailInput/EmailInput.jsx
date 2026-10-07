import { useState } from 'react';
import './EmailInput.css';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEnvelope } from '@fortawesome/free-solid-svg-icons';
import { validateEmail } from '../../../../utils/validators.js';

function EmailInput({ placeholder, value, onChange }) {
  const [touched, setTouched] = useState(false);

  const showError = touched && value !== '' && !validateEmail(value);

  return (
    <div className="EmailInputWrapper">
      <div className="EmailInputRoot">
        <span className="EmailIcon">
          <FontAwesomeIcon icon={faEnvelope} />
        </span>
        <input
          className={`EmailInputContainer ${showError ? 'is-invalid' : ''}`}
          type="email"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => setTouched(true)}
          aria-invalid={showError}
        />
      </div>
      {showError && <p className="EmailError">Ingresa un correo válido.</p>}
    </div>
  );
}

export default EmailInput;