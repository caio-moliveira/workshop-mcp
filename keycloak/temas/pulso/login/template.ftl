<#-- Moldura de todas as telas de login do pulso. (FE §9): painel da marca à esquerda (55%) e o
     formulário à direita (45%). Parte do template.ftl do tema `base` do Keycloak 26.4.2; muda só a
     estrutura do corpo. As telas (login.ftl, error.ftl...) continuam as do `base` e preenchem as
     seções "header", "form", "socialProviders" e "info". -->
<#import "footer.ftl" as loginFooter>
<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html class="${properties.kcHtmlClass!}" lang="${lang}"<#if realm.internationalizationEnabled> dir="${(locale.rtl)?then('rtl','ltr')}"</#if>>

<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex, nofollow" />
    <title>${msg("loginTitle",(realm.displayName!''))}</title>
    <link rel="icon" type="image/svg+xml" href="${url.resourcesPath}/img/marca.svg" />
    <link rel="preload" href="${url.resourcesPath}/fontes/geist-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin />
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <script type="importmap">
        {
            "imports": {
                "rfc4648": "${url.resourcesCommonPath}/vendor/rfc4648/rfc4648.js"
            }
        }
    </script>
    <script src="${url.resourcesPath}/js/menu-button-links.js" type="module"></script>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <script type="module">
        import { startSessionPolling } from "${url.resourcesPath}/js/authChecker.js";

        startSessionPolling(
            "${url.ssoLoginInOtherTabsUrl?no_esc}"
        );
    </script>
    <script type="module">
        document.addEventListener("click", (event) => {
            const link = event.target.closest("a[data-once-link]");

            if (!link) {
                return;
            }

            if (link.getAttribute("aria-disabled") === "true") {
                event.preventDefault();
                return;
            }

            const { disabledClass } = link.dataset;

            if (disabledClass) {
                link.classList.add(...disabledClass.trim().split(/\s+/));
            }

            link.setAttribute("role", "link");
            link.setAttribute("aria-disabled", "true");
        });
    </script>
    <#if authenticationSession??>
        <script type="module">
            import { checkAuthSession } from "${url.resourcesPath}/js/authChecker.js";

            checkAuthSession(
                "${authenticationSession.authSessionIdHash}"
            );
        </script>
    </#if>
</head>

<body class="${bodyClass}" data-page-id="login-${pageId}">
<div class="${properties.kcLoginClass!}">
    <aside class="pulso-painel-da-marca">
        <div class="pulso-marca">
            <svg class="pulso-monograma" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
                <rect width="32" height="32" rx="8" fill="#F7F8F5"/>
                <path d="M11 23V9h5.5a4.5 4.5 0 0 1 0 9H11" fill="none" stroke="#202C29" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="22.5" cy="22" r="2.2" fill="#202C29"/>
            </svg>
            <span class="pulso-nome">pulso.</span>
        </div>

        <div class="pulso-proposta">
            <p class="pulso-frase">${msg("pulsoFraseDeValor")}</p>
            <p class="pulso-apoio">${msg("pulsoApoio")}</p>
        </div>

        <#-- Detalhe gráfico abstrato: uma linha de pulso fina sobre uma régua, sem imagem nem gradiente. -->
        <svg class="pulso-detalhe" viewBox="0 0 240 72" aria-hidden="true" focusable="false">
            <line x1="0" y1="56" x2="240" y2="56" class="pulso-detalhe-regua"/>
            <line x1="48" y1="52" x2="48" y2="60" class="pulso-detalhe-regua"/>
            <line x1="120" y1="52" x2="120" y2="60" class="pulso-detalhe-regua"/>
            <line x1="192" y1="52" x2="192" y2="60" class="pulso-detalhe-regua"/>
            <polyline points="0,40 64,40 78,40 90,14 104,50 116,28 128,40 176,40 188,32 200,32" class="pulso-detalhe-linha"/>
            <circle cx="200" cy="32" r="4" class="pulso-detalhe-ponto"/>
        </svg>
    </aside>

    <main class="pulso-lado-do-formulario">
    <div class="${properties.kcFormCardClass!}">
        <header class="${properties.kcFormHeaderClass!}">
            <#if realm.internationalizationEnabled  && locale.supported?size gt 1>
                <div class="${properties.kcLocaleMainClass!}" id="kc-locale">
                    <div id="kc-locale-wrapper" class="${properties.kcLocaleWrapperClass!}">
                        <div id="kc-locale-dropdown" class="menu-button-links ${properties.kcLocaleDropDownClass!}">
                            <button tabindex="1" id="kc-current-locale-link" aria-label="${msg("languages")}" aria-haspopup="true" aria-expanded="false" aria-controls="language-switch1">${locale.current}</button>
                            <ul role="menu" tabindex="-1" aria-labelledby="kc-current-locale-link" aria-activedescendant="" id="language-switch1" class="${properties.kcLocaleListClass!}">
                                <#assign i = 1>
                                <#list locale.supported as l>
                                    <li class="${properties.kcLocaleListItemClass!}" role="none">
                                        <a role="menuitem" id="language-${i}" class="${properties.kcLocaleItemClass!}" href="${l.url}">${l.label}</a>
                                    </li>
                                    <#assign i++>
                                </#list>
                            </ul>
                        </div>
                    </div>
                </div>
            </#if>
            <#if !(auth?has_content && auth.showUsername() && !auth.showResetCredentials())>
                <h1 id="kc-page-title"><#nested "header"></h1>
                <#if pageId == "login">
                    <p class="pulso-instrucao">${msg("pulsoInstrucao")}</p>
                </#if>
            <#else>
                <#nested "show-username">
                <div id="kc-username" class="${properties.kcFormGroupClass!}">
                    <label id="kc-attempted-username">${auth.attemptedUsername}</label>
                    <a id="reset-login" href="${url.loginRestartFlowUrl}">${msg("restartLoginTooltip")}</a>
                </div>
            </#if>
            <#if displayRequiredFields>
                <p class="pulso-obrigatorios"><span class="required">*</span> ${msg("requiredFields")}</p>
            </#if>
        </header>
        <div id="kc-content">
            <div id="kc-content-wrapper">

            <#-- Ações iniciadas pela aplicação não mostram avisos sobre completar a própria ação. -->
            <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                <div class="alert-${message.type} ${properties.kcAlertClass!}" role="<#if message.type = 'error'>alert<#else>status</#if>">
                    <span class="${properties.kcAlertTitleClass!}">${kcSanitize(message.summary)?no_esc}</span>
                </div>
            </#if>

            <#nested "form">

            <#if auth?has_content && auth.showTryAnotherWayLink()>
                <form id="kc-select-try-another-way-form" action="${url.loginAction}" method="post">
                    <div class="${properties.kcFormGroupClass!}">
                        <input type="hidden" name="tryAnotherWay" value="on"/>
                        <a href="#" id="try-another-way"
                           onclick="document.forms['kc-select-try-another-way-form'].requestSubmit();return false;">${msg("doTryAnotherWay")}</a>
                    </div>
                </form>
            </#if>

            <#nested "socialProviders">

            <#if displayInfo>
                <div id="kc-info" class="${properties.kcSignUpClass!}">
                    <div id="kc-info-wrapper" class="${properties.kcInfoAreaWrapperClass!}">
                        <#nested "info">
                    </div>
                </div>
            </#if>
            </div>
        </div>

        <@loginFooter.content/>
    </div>
    </main>
</div>
</body>
</html>
</#macro>
