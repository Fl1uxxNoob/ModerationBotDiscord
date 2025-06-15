import discord
from discord import app_commands
from discord.ext import commands
from database import add_warning, get_warnings
import yaml

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.yml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def has_permissions(self, interaction: discord.Interaction) -> bool:
        """Controlla se l'utente ha i permessi di moderazione"""
        return interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.moderate_members

    @app_commands.command(name='warn', description='Assegna un avvertimento a un utente')
    @app_commands.describe(member='Utente da avvertire', reason='Motivo dell\'avvertimento')
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # Controllo permessi
        if not self.has_permissions(interaction):
            await interaction.response.send_message("❌ Non hai i permessi per usare questo comando!", ephemeral=True)
            return

        # Controllo se l'utente può essere avvertito
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Non puoi avvertire questo utente!", ephemeral=True)
            return

        # Non permettere di avvertire se stessi
        if member == interaction.user:
            await interaction.response.send_message("❌ Non puoi avvertire te stesso!", ephemeral=True)
            return

        # Non permettere di avvertire bot
        if member.bot:
            await interaction.response.send_message("❌ Non puoi avvertire un bot!", ephemeral=True)
            return

        try:
            add_warning(member.id, interaction.user.id, reason)
            count = get_warnings(member.id)
            
            msg = self.config['messages']['warn_message'].format(
                member=member.mention, reason=reason, count=count
            )
            await interaction.response.send_message(msg)
            
            # Log dell'azione
            print(f"⚠️ {member} avvertito da {interaction.user}. Motivo: {reason}. Totale avvertimenti: {count}")
            
            # Invia DM all'utente avvertito
            try:
                embed = discord.Embed(
                    title="Hai ricevuto un avvertimento",
                    description=f"Hai ricevuto un avvertimento in **{interaction.guild.name}**",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Motivo", value=reason, inline=False)
                embed.add_field(name="Moderatore", value=interaction.user.mention, inline=False)
                embed.add_field(name="Avvertimenti totali", value=str(count), inline=False)
                await member.send(embed=embed)
            except:
                pass  # Ignora se non può inviare DM
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Errore nell'assegnare l'avvertimento: {str(e)}", ephemeral=True)

    @app_commands.command(name='warnings', description='Mostra gli avvertimenti di un utente')
    @app_commands.describe(member='Utente di cui vedere gli avvertimenti')
    async def show_warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        # Se non viene specificato un membro, mostra i propri avvertimenti
        if member is None:
            member = interaction.user
        
        # Solo moderatori possono vedere gli avvertimenti di altri utenti
        if member != interaction.user and not self.has_permissions(interaction):
            await interaction.response.send_message("❌ Non hai i permessi per vedere gli avvertimenti di altri utenti!", ephemeral=True)
            return

        count = get_warnings(member.id)
        
        embed = discord.Embed(
            title=f"Avvertimenti di {member.display_name}",
            description=f"**Totale avvertimenti:** {count}",
            color=discord.Color.yellow() if count > 0 else discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if count == 0:
            embed.add_field(name="Stato", value="✅ Nessun avvertimento", inline=False)
        else:
            embed.add_field(name="Stato", value=f"⚠️ {count} avvertimenti", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Warnings(bot))