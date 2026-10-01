import React from 'react';
import './Login.css';
import EmailInput from './EmailInput/EmailInput.jsx';
import PassInput from './PassInput/PassInput.jsx';

function Login() {
  return(
    <div className="LoginBackground">
        <div className="LoginContainer">
                <div className="LoginLogo"> <img src="./src/assets/logo.png" /> </div>
            <div className="LoginTitleContainer">

                <div className="LoginTitle">Akash Store</div>
                <div className="LoginSubtitle">Panel de Administración de ejemplo
                </div>
            </div>

            <form className="LoginForm">
                <EmailInput/>
                <PassInput/>

                <button type="submit" className="LoginButton">Login</button>
            </form>

        </div>
    </div>

    
    );
}

export default Login;