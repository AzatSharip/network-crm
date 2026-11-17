import { test,expect } from '@playwright/test'
const email=process.env.CRM_E2E_EMAIL||'demo@example.com'
const password=process.env.CRM_E2E_PASSWORD
if(!password)throw new Error('CRM_E2E_PASSWORD required; synthetic local account only')
async function login(page:any){await page.goto('/');await page.getByLabel('Email',{exact:true}).fill(email);await page.getByLabel('Пароль',{exact:true}).fill(password!);await page.getByRole('button',{name:'Войти',exact:true}).click();await expect(page.getByRole('heading',{name:/Контакты/})).toBeVisible()}
test('create dynamic contacts, search, edit, relationship, graph, Inbox and logout',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await login(page)
 await page.getByLabel('Рабочее пространство').selectOption({label:'◎ Семья'})
 await page.getByRole('button',{name:'Добавить контакт',exact:true}).click()
 const name='Браузерный Тест '+Date.now();await page.getByLabel('Имя / ФИО').fill(name)
 await page.getByLabel('Город',{exact:true}).fill('Уфа');await page.getByLabel('Профессия',{exact:true}).fill('Стоматолог')
 await page.getByRole('button',{name:'Добавить способ связи'}).click();await page.getByLabel('Платформа 1',{exact:true}).selectOption('telegram');await page.getByLabel('Вид идентификатора 1',{exact:true}).selectOption('numeric_id');await page.getByLabel('Значение 1',{exact:true}).fill(String(Date.now()))
 await page.getByRole('button',{name:'Добавить способ связи'}).click();await page.getByLabel('Платформа 2',{exact:true}).selectOption('email');await page.getByLabel('Значение 2',{exact:true}).fill('browser'+Date.now()+'@example.com')
 await page.getByRole('button',{name:'Добавить контакт',exact:true}).last().click();await expect(page.getByRole('heading',{name,exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Редактировать',exact:true}).click();await page.getByLabel('Страна',{exact:true}).fill('Казахстан');await page.getByRole('button',{name:'Сохранить изменения'}).click();await expect(page.getByText('Уфа, Казахстан',{exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Все контакты'}).click();await page.getByLabel('Поиск контактов').fill(name);await expect(page.getByRole('button',{name:name+' Стоматолог'})).toBeVisible()
 await page.getByRole('button',{name:'Открыть '+name,exact:true}).click();await page.getByRole('button',{name:'Добавить связь',exact:true}).click();await page.getByLabel('Поиск: Связанный человек').fill('Александр');await expect(page.getByLabel('Связанный человек',{exact:true}).locator('option')).toHaveCount(2);await page.getByLabel('Связанный человек',{exact:true}).selectOption({label:'Александр Тестов'});await page.getByRole('button',{name:'Сохранить связь'}).click();await expect(page.getByRole('button',{name:'Александр Тестов',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Открыть граф'}).click();await page.getByRole('button',{name:'Показать связи'}).click();await expect(page.locator('.graph-canvas canvas').first()).toBeVisible();await expect(page.getByText(/людей · нажмите/)).toBeVisible()
 await page.getByRole('button',{name:'AI Inbox',exact:true}).click();await expect(page.getByRole('heading',{name:'AI Inbox',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Выйти',exact:true}).click();await expect(page.getByRole('heading',{name:'Рады видеть вас'})).toBeVisible();expect(errors).toEqual([])
})
test('mobile layout and keyboard editor',async({page})=>{
 await page.setViewportSize({width:390,height:844});await login(page)
 await page.getByRole('button',{name:'Добавить контакт',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByLabel('Имя / ФИО')).toBeFocused();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy()
 await page.screenshot({path:'../.ai/scratch/mobile.png',fullPage:true})
})
