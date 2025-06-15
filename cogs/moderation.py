import discord
from discord import app_commands
from discord.ext import commands, tasks
import yaml
from datetime import datetime, timedelta
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.yml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.temp_bans = {}  # Dizionario per gestire i ban temporanei
        self.temp_mutes = {}  # Dizionario per gestire i mute temporanei

    def get_role(self, guild, role_name):
        """Ottiene un ruolo per nome"""
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            raise ValueError(f"Ruolo '{role_name}' non trovato nel server!")
        return role

    def has_permissions(self, interaction: discord.Interaction) -> bool:
        """Controlla se l'utente ha i permessi di moderazione"""
        return interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.moderate_members

    @app_commands.command(name='mute', description='Muta un utente per un periodo specificato')
    @app_commands.describe(
        member='Utente da mutare',
        duration='Durata in minuti',
        reason='Motivo del mute'
    )
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "Nessun motivo specificato"):
        # Controllo permessi
        if not self.has_permissions(interaction):
            await interaction.response.send_message("❌ Non hai i permessi per usare questo comando!", ephemeral=True)
            return

        # Controllo se l'utente può essere mutato
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Non puoi mutare questo utente!", ephemeral=True)
            return

        try:
            # CORREZIONE: Usa discord.utils.utcnow() per datetime timezone-aware
            timeout_until = discord.utils.utcnow() + timedelta(minutes=duration)
            await member.timeout(timeout_until, reason=reason)
            
            # CORREZIONE: Assegna anche il ruolo "Muted" se esiste
            muted_role = None
            try:
                muted_role = self.get_role(interaction.guild, self.config['roles']['muted'])
                if muted_role not in member.roles:
                    await member.add_roles(muted_role, reason=f"Mutato da {interaction.user}")
                    print(f"🔇 Aggiunto ruolo {muted_role.name} a {member}")
                    
                    # NUOVO: Programma la rimozione automatica del ruolo
                    unmute_time = discord.utils.utcnow() + timedelta(minutes=duration)
                    self.temp_mutes[member.id] = {
                        'guild': interaction.guild.id,
                        'unmute_time': unmute_time,
                        'role': muted_role.id
                    }
                    # Avvia task per rimuovere il ruolo automaticamente
                    asyncio.create_task(self.schedule_unmute(member.id, duration * 60))  # Secondi
                    
            except ValueError:
                # Il ruolo "Muted" non esiste, usa solo il timeout
                print(f"⚠️ Ruolo 'Muted' non trovato, uso solo timeout per {member}")
            except Exception as role_error:
                print(f"⚠️ Errore nell'assegnare il ruolo muted: {role_error}")
            
            # Messaggio di conferma
            msg = self.config['messages']['mute_success'].format(
                member=member.mention, 
                duration=f"{duration} minuti", 
                reason=reason
            )
            await interaction.response.send_message(msg)
            
            # Log dell'azione
            print(f"🔇 {member} mutato da {interaction.user} per {duration} minuti. Motivo: {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Non ho i permessi per mutare questo utente!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Errore nel mutare l'utente: {str(e)}", ephemeral=True)

    @app_commands.command(name='unmute', description='Rimuove il mute da un utente')
    @app_commands.describe(member='Utente da smutare')
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        if not self.has_permissions(interaction):
            await interaction.response.send_message("❌ Non hai i permessi per usare questo comando!", ephemeral=True)
            return

        try:
            # CORREZIONE: Rimuove il timeout di Discord
            await member.timeout(None)
            
            # CORREZIONE: Rimuove anche il ruolo "Muted" se presente
            try:
                muted_role = self.get_role(interaction.guild, self.config['roles']['muted'])
                if muted_role in member.roles:
                    await member.remove_roles(muted_role, reason=f"Smutato da {interaction.user}")
                    print(f"🔊 Rimosso ruolo {muted_role.name} da {member}")
            except ValueError:
                # Il ruolo "Muted" non esiste, ignora
                pass
            except Exception as role_error:
                print(f"⚠️ Errore nel rimuovere il ruolo muted: {role_error}")
            
            # NUOVO: Rimuovi dal dizionario dei mute temporanei se presente
            if member.id in self.temp_mutes:
                del self.temp_mutes[member.id]
                print(f"🔊 Rimosso {member} dai mute temporanei")
            
            await interaction.response.send_message(f"✅ {member.mention} è stato smutato.")
            print(f"🔊 {member} smutato da {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Non ho i permessi per smutare questo utente!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Errore: {str(e)}", ephemeral=True)

    @app_commands.command(name='kick', description='Espelle un utente dal server')
    @app_commands.describe(
        member='Utente da espellere',
        reason='Motivo dell\'espulsione'
    )
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Nessun motivo specificato"):
        # Controllo permessi
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("❌ Non hai i permessi per espellere utenti!", ephemeral=True)
            return

        # Controllo ruoli
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Non puoi espellere questo utente!", ephemeral=True)
            return

        try:
            # Invia DM all'utente prima dell'espulsione
            try:
                embed = discord.Embed(
                    title="Sei stato espulso",
                    description=f"Sei stato espulso da **{interaction.guild.name}**",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Motivo", value=reason, inline=False)
                embed.add_field(name="Moderatore", value=interaction.user.mention, inline=False)
                await member.send(embed=embed)
            except:
                pass  # Ignora se non può inviare DM

            await member.kick(reason=f"{reason} | Moderatore: {interaction.user}")
            
            msg = self.config['messages']['kick_success'].format(
                member=member.mention,
                reason=reason
            )
            await interaction.response.send_message(msg)
            
            print(f"👢 {member} espulso da {interaction.user}. Motivo: {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Non ho i permessi per espellere questo utente!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Errore: {str(e)}", ephemeral=True)

    @app_commands.command(name='ban', description='Banna un utente dal server')
    @app_commands.describe(
        member='Utente da bannare',
        duration='Durata in giorni (0 = permanente)',
        reason='Motivo del ban'
    )
    async def ban(self, interaction: discord.Interaction, member: discord.Member, duration: int = 0, reason: str = "Nessun motivo specificato"):
        # Controllo permessi
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ Non hai i permessi per bannare utenti!", ephemeral=True)
            return

        # Controllo ruoli
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Non puoi bannare questo utente!", ephemeral=True)
            return

        try:
            # Invia DM all'utente prima del ban
            try:
                embed = discord.Embed(
                    title="Sei stato bannato",
                    description=f"Sei stato bannato da **{interaction.guild.name}**",
                    color=discord.Color.red()
                )
                embed.add_field(name="Motivo", value=reason, inline=False)
                embed.add_field(name="Durata", value=f"{duration} giorni" if duration > 0 else "Permanente", inline=False)
                embed.add_field(name="Moderatore", value=interaction.user.mention, inline=False)
                await member.send(embed=embed)
            except:
                pass

            await member.ban(reason=f"{reason} | Moderatore: {interaction.user}")
            
            # Programma l'unban se temporaneo
            if duration > 0:
                # CORREZIONE: Usa discord.utils.utcnow() anche qui
                unban_time = discord.utils.utcnow() + timedelta(days=duration)
                self.temp_bans[member.id] = {
                    'guild': interaction.guild.id,
                    'unban_time': unban_time,
                    'reason': reason
                }
                # Avvia task per l'unban automatico
                asyncio.create_task(self.schedule_unban(member.id, duration * 24 * 60 * 60))  # Secondi
                duration_text = f"{duration} giorni"
            else:
                duration_text = "permanente"
            
            msg = self.config['messages']['ban_success'].format(
                member=member.mention,
                duration=duration_text,
                reason=reason
            )
            await interaction.response.send_message(msg)
            
            print(f"⛔ {member} bannato da {interaction.user} per {duration_text}. Motivo: {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Non ho i permessi per bannare questo utente!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Errore: {str(e)}", ephemeral=True)

    async def schedule_unban(self, user_id: int, seconds: int):
        """Programma un unban automatico"""
        await asyncio.sleep(seconds)
        if user_id in self.temp_bans:
            guild_id = self.temp_bans[user_id]['guild']
            guild = self.bot.get_guild(guild_id)
            if guild:
                try:
                    await guild.unban(discord.Object(id=user_id), reason="Ban temporaneo scaduto")
                    print(f"🔓 Utente {user_id} sbannato automaticamente")
                except:
                    print(f"❌ Errore nell'unban automatico di {user_id}")
            del self.temp_bans[user_id]

    async def schedule_unmute(self, user_id: int, seconds: int):
        """Programma la rimozione automatica del ruolo muted"""
        await asyncio.sleep(seconds)
        if user_id in self.temp_mutes:
            guild_id = self.temp_mutes[user_id]['guild']
            role_id = self.temp_mutes[user_id]['role']
            guild = self.bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                role = guild.get_role(role_id)
                if member and role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Mute temporaneo scaduto")
                        print(f"🔊 Ruolo {role.name} rimosso automaticamente da {member}")
                    except Exception as e:
                        print(f"❌ Errore nella rimozione automatica del ruolo muted da {user_id}: {e}")
            del self.temp_mutes[user_id]

    @app_commands.command(name='unban', description='Rimuove il ban da un utente')
    @app_commands.describe(user_id='ID dell\'utente da sbannare')
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ Non hai i permessi per sbannare utenti!", ephemeral=True)
            return

        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
            await interaction.guild.unban(user, reason=f"Sbannato da {interaction.user}")
            
            # Rimuovi dal dizionario dei ban temporanei se presente
            if user_id in self.temp_bans:
                del self.temp_bans[user_id]
            
            await interaction.response.send_message(f"✅ {user.mention} è stato sbannato.")
            print(f"🔓 {user} sbannato da {interaction.user}")
            
        except ValueError:
            await interaction.response.send_message("❌ ID utente non valido!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Utente non trovato o non bannato!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Errore: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))