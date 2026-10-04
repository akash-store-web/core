import React from 'react';
import './Login.css';
import EmailInput from './EmailInput/EmailInput.jsx';
import PassInput from './PassInput/PassInput.jsx';
import { useNavigate } from 'react-router-dom';

function Login() {
  const navigate = useNavigate();

    function handleSubmit(e) {
    e.preventDefault();
    }
    
  return(
    <div className="LoginBackground">
        <div className="LoginContainer">
                <div className="LoginLogo"> <img src="./src/assets/logo.png" /> </div>
            <div className="LoginTitleContainer">

                <div className="LoginTitle">Akash Store</div>
                <div className="LoginSubtitle">Panel de Admin
                </div>
            </div>

            <form className="LoginForm">
                <EmailInput placeholder="Email"/>
                <PassInput placeholder="Password"/>

                <button type="submit" className="LoginButton">Ingresar</button>
                <div className="Repair"> <a href="#">¿Olvidaste tu contraseña?</a></div>
            </form>

        </div>
    </div>

    
    );}

export default Login;